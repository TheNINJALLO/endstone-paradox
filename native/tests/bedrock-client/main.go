// An offline, scripted protocol client for isolated acceptance servers only.
package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/df-mc/go-nethernet"
	"github.com/df-mc/go-nethernet/discovery"
	"github.com/df-mc/go-nethernet/endpoint"
	"github.com/go-gl/mathgl/mgl32"
	"github.com/google/uuid"
	"github.com/sandertv/gophertunnel/minecraft"
	"github.com/sandertv/gophertunnel/minecraft/protocol"
	"github.com/sandertv/gophertunnel/minecraft/protocol/login"
	"github.com/sandertv/gophertunnel/minecraft/protocol/packet"
)

var output sync.Mutex

func event(name, kind string, value any) {
	output.Lock()
	defer output.Unlock()
	_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"name": name, "event": kind, "value": value})
}

type Bot struct {
	name              string
	conn              *minecraft.Conn
	mu                sync.Mutex
	pos               mgl32.Vec3
	tick              uint64
	yaw               float32
	walking, teleport bool
	rate              int
	sent, corrected   uint64
	done              chan struct{}
}

func (b *Bot) read() {
	defer close(b.done)
	for {
		p, err := b.conn.ReadPacket()
		if err != nil {
			event(b.name, "closed", err.Error())
			return
		}
		b.mu.Lock()
		switch p := p.(type) {
		case *packet.MovePlayer:
			if p.EntityRuntimeID == b.conn.GameData().EntityRuntimeID {
				b.pos = p.Position
				b.teleport = p.Mode == packet.MoveModeTeleport
				event(b.name, "move", p.Position)
			}
		case *packet.CorrectPlayerMovePrediction:
			b.pos = p.Position
			b.corrected++
		case *packet.NetworkStackLatency:
			if p.NeedsResponse {
				_ = b.conn.WritePacket(&packet.NetworkStackLatency{Timestamp: p.Timestamp})
			}
		case *packet.Text:
			event(b.name, "text", p.Message)
		case *packet.CommandOutput:
			event(b.name, "command_output", p.OutputMessages)
		case *packet.ModalFormRequest:
			event(b.name, "form", string(p.FormData))
			_ = b.conn.WritePacket(&packet.ModalFormResponse{FormID: p.FormID, CancelReason: protocol.Option(uint8(packet.ModalFormCancelReasonUserClosed))})
		case *packet.UpdateAttributes:
			if p.EntityRuntimeID == b.conn.GameData().EntityRuntimeID {
				event(b.name, "attributes", p.Attributes)
			}
		case *packet.ChangeDimension:
			b.pos = p.Position
			b.teleport = true
			_ = b.conn.WritePacket(&packet.PlayerAction{EntityRuntimeID: b.conn.GameData().EntityRuntimeID, ActionType: protocol.PlayerActionDimensionChangeDone})
		}
		b.mu.Unlock()
	}
}
func (b *Bot) input() {
	ticker := time.NewTicker(time.Millisecond * 5)
	defer ticker.Stop()
	next := time.Now()
	nextReport := next.Add(time.Second)
	lastRate := 20
	for {
		select {
		case <-b.done:
			return
		case now := <-ticker.C:
			b.mu.Lock()
			if b.rate != lastRate {
				next = now
				lastRate = b.rate
			}
			if b.rate <= 0 || now.Before(next) {
				b.mu.Unlock()
				continue
			}
			next = next.Add(time.Second / time.Duration(b.rate))
			if now.Sub(next) > time.Second {
				next = now
			}
			flags := protocol.NewInputFlags(packet.InputFlagCount)
			flags.Set(packet.InputFlagVerticalCollision)
			if b.teleport {
				flags.Set(packet.InputFlagHandledTeleport)
				b.teleport = false
			}
			var move mgl32.Vec2
			var delta mgl32.Vec3
			if b.walking {
				// Flat test arena, ordinary walking speed; server corrections win.
				move = mgl32.Vec2{0, 1}
				flags.Set(packet.InputFlagUp)
				if (b.tick/100)%2 == 0 {
					b.yaw = 0
					delta[2] = 0.215
				} else {
					b.yaw = 180
					delta[2] = -0.215
				}
				b.pos = b.pos.Add(delta)
			}
			yaw := float64(b.yaw) * math.Pi / 180
			camera := mgl32.Vec3{float32(-math.Sin(yaw)), 0, float32(math.Cos(yaw))}
			p := &packet.PlayerAuthInput{Position: b.pos, Delta: delta, Yaw: b.yaw, HeadYaw: b.yaw, MoveVector: move, RawMoveVector: move, AnalogueMoveVector: move, CameraOrientation: camera, InputMode: packet.InputModeMouse, PlayMode: packet.PlayModeNormal, InteractionModel: packet.InteractionModelCrosshair, InputData: flags, Tick: b.tick}
			b.tick++
			b.sent++
			err := b.conn.WritePacket(p)
			if now.After(nextReport) {
				event(b.name, "state", map[string]any{"position": b.pos, "sent": b.sent, "corrected": b.corrected, "tick": b.tick})
				nextReport = now.Add(time.Second)
			}
			b.mu.Unlock()
			if err != nil {
				event(b.name, "write_error", err.Error())
				return
			}
		}
	}
}
func main() {
	address := flag.String("address", "http://127.0.0.1:39301", "Isolated offline test server")
	transport := flag.String("transport", "nethernet", "nethernet, lan or raknet")
	control := flag.String("control", "", "Append-only JSON command file")
	names := flag.String("names", "ParadoxTestA,ParadoxTestB", "Test names")
	duration := flag.Duration("duration", 20*time.Minute, "Maximum run duration")
	flag.Parse()
	ctx, cancel := context.WithTimeout(context.Background(), *duration)
	defer cancel()
	bots := map[string]*Bot{}
	for _, name := range strings.Split(*names, ",") {
		dial := minecraft.Dialer{IdentityData: login.IdentityData{DisplayName: name, Identity: uuid.NewString()}, FlushRate: time.Millisecond * 5}
		var conn *minecraft.Conn
		var err error
		dialCtx, dialCancel := context.WithTimeout(ctx, 45*time.Second)
		if *transport == "raknet" {
			conn, err = dial.DialContext(dialCtx, "raknet", *address)
		} else if *transport == "lan" {
			host, _, _ := net.SplitHostPort(*address)
			dial.ClientData.ServerAddress = *address
			cfg := discovery.ListenConfig{BroadcastAddress: &net.UDPAddr{IP: net.ParseIP(host), Port: 7551}}
			var signal *discovery.Listener
			signal, err = cfg.Listen(":0")
			if err == nil {
				defer signal.Close()
				var networkID uint64
				for networkID == 0 && dialCtx.Err() == nil {
					for id, response := range signal.Responses() {
						// BDS 1.26.51 advertises discovery v7; the library's full metadata
						// decoder supports v6. Match both unique test fixture labels in
						// the response sent to our explicit unicast address instead.
						if bytes.Contains(response, []byte("Paradox acceptance test")) && bytes.Contains(response, []byte("paradox-acceptance")) {
							event(name, "test_server_discovered", "Paradox acceptance test / paradox-acceptance")
							networkID = id
							break
						}
					}
					time.Sleep(100 * time.Millisecond)
				}
				if networkID == 0 {
					err = fmt.Errorf("LAN discovery timed out")
				} else {
					conn, err = dial.DialContextNetwork(dialCtx, minecraft.NetherNet{Signaling: signal, Dialer: nethernet.Dialer{AllowIdentitylessServer: true}}, strconv.FormatUint(networkID, 10))
				}
			}
		} else {
			conn, err = dial.DialContextNetwork(dialCtx, minecraft.NetherNet{Signaling: endpoint.NewClient()}, *address)
		}
		if err != nil {
			event(name, "dial_error", err.Error())
			os.Exit(1)
		}
		if err = conn.DoSpawnContext(dialCtx); err != nil {
			event(name, "spawn_error", err.Error())
			os.Exit(1)
		}
		dialCancel()
		_ = conn.WritePacket(&packet.ServerBoundLoadingScreen{Type: packet.LoadingScreenTypeEnd})
		b := &Bot{name: name, conn: conn, pos: conn.GameData().PlayerPosition, rate: 20, done: make(chan struct{})}
		bots[name] = b
		event(name, "spawn", map[string]any{"position": b.pos, "runtime_id": conn.GameData().EntityRuntimeID, "protocol": protocol.CurrentProtocol})
		go b.read()
		go b.input()
		defer conn.Close()
	}
	handle := func(line []byte) {
		var cmd struct {
			Name   string `json:"name"`
			Action string `json:"action"`
			Value  string `json:"value"`
			Rate   int    `json:"rate"`
			Slot   uint32 `json:"slot"`
		}
		if json.Unmarshal(line, &cmd) != nil {
			return
		}
		if cmd.Action == "stop" {
			cancel()
			return
		}
		b := bots[cmd.Name]
		if b == nil {
			return
		}
		b.mu.Lock()
		switch cmd.Action {
		case "walk":
			b.walking = cmd.Value == "on"
		case "rate":
			b.rate = cmd.Rate
		case "command":
			_ = b.conn.WritePacket(&packet.CommandRequest{CommandLine: cmd.Value, CommandOrigin: protocol.CommandOrigin{Origin: protocol.CommandOriginPlayer, UUID: uuid.New()}, Version: "latest"})
		case "hotbar":
			_ = b.conn.WritePacket(&packet.PlayerHotBar{SelectedHotBarSlot: cmd.Slot, SelectHotBarSlot: true})
		case "attack":
			if target := bots[cmd.Value]; target != nil {
				_ = b.conn.WritePacket(&packet.InventoryTransaction{TransactionData: &protocol.UseItemOnEntityTransactionData{TargetEntityRuntimeID: target.conn.GameData().EntityRuntimeID, ActionType: protocol.UseItemOnEntityActionAttack, Position: b.pos, ClickedPosition: mgl32.Vec3{0, 1, 0}}})
			}
		case "look":
			_, _ = fmt.Sscan(cmd.Value, &b.yaw)
		case "close":
			_ = b.conn.Close()
		}
		b.mu.Unlock()
		event(b.name, "action", cmd.Action)
	}
	go func() {
		if *control == "" {
			scanner := bufio.NewScanner(os.Stdin)
			for scanner.Scan() {
				handle(scanner.Bytes())
			}
			return
		}
		seen := 0
		for ctx.Err() == nil {
			data, _ := os.ReadFile(*control)
			lines := strings.Split(string(data), "\n")
			for seen < len(lines)-1 {
				handle([]byte(lines[seen]))
				seen++
			}
			time.Sleep(100 * time.Millisecond)
		}
	}()
	<-ctx.Done()
	fmt.Fprintln(os.Stderr, "Acceptance client finished")
}
