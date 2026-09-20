"""Two-client acceptance tests against a disposable, running acceptance-server.

Requires the isolated paradox-acceptance-client container with NET_ADMIN.
Network impairment applies only to that test container's eth0 interface.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

p = argparse.ArgumentParser()
p.add_argument("output", type=Path)
p.add_argument("--server-container", default="paradox-native-build")
p.add_argument("--client-container", default="paradox-acceptance-client")
p.add_argument("--client-binary", default="/work/scratch/validation/bedrock-client")
p.add_argument("--server-path", default="/runtime/paradox")
p.add_argument("--address", default="172.17.0.6:39301")
p.add_argument("--transport", default="lan", choices=("lan", "raknet"))
args = p.parse_args()
root = Path(__file__).resolve().parents[2]
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
client_control = out / "client-control.ndjson"
client_control.write_text("")
checks = {}
phases = []
events = []
seen = set()
started = time.time()


def run(*cmd, **kwargs):
    return subprocess.run(
        cmd, check=True, text=True, capture_output=True, **kwargs
    ).stdout


def netem(*options):
    run(
        "docker",
        "exec",
        args.client_container,
        "tc",
        "qdisc",
        "replace",
        "dev",
        "eth0",
        "root",
        "netem",
        *options,
    )


def server_python(code):
    if args.server_container:
        return json.loads(
            run(
                "docker",
                "exec",
                "-i",
                args.server_container,
                "/opt/endstone-python/bin/python",
                "-",
                input=code,
            )
        )
    return json.loads(run(sys.executable, "-c", code))


def status():
    return server_python(
        "import json,urllib.request;from pathlib import Path;"
        f"token=Path({args.server_path!r}+'/plugins/paradox/web-token.txt').read_text().strip();"
        "r=urllib.request.Request('http://127.0.0.1:39303/api/status',headers={'Authorization':'Bearer '+token});"
        "print(json.dumps(json.load(urllib.request.urlopen(r,timeout=5))))"
    )


def table(name):
    assert name in ("homes", "bans", "players", "pvp_data")
    return server_python(
        "import sqlite3,json;"
        f"c=sqlite3.connect({args.server_path!r}+'/plugins/paradox/paradox.db');"
        f"exists=c.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',{name!r})).fetchone();"
        f"rows=c.execute('SELECT key,value FROM {name}').fetchall() if exists else [];"
        "print(json.dumps({k:json.loads(v) for k,v in rows}))"
    )


def console(command):
    with (out / "control.ndjson").open("a") as f:
        f.write(json.dumps({"command": command}) + "\n")


def action(name="ParadoxTestA", **fields):
    with client_control.open("a") as f:
        f.write(json.dumps({"name": name, **fields}) + "\n")


def require(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise AssertionError(name)


def monitor(label, seconds, *, enforce_clean=True):
    print(label, flush=True)
    end = time.monotonic() + seconds
    samples = []
    if enforce_clean:
        checks.setdefault(label + "_no_false_enforcement", True)
        checks.setdefault(label + "_no_robotic_pathing", True)
    while time.monotonic() < end:
        s = status()
        samples.append(s)
        with (out / "network-samples.ndjson").open("a") as f:
            f.write(json.dumps({"phase": label, "time": time.time(), **s}) + "\n")
        if enforce_clean:
            require(label + "_both_connected", len(s["players"]) == 2)
            for entry in s["evidence"]:
                key = (entry["uuid"], entry["module"], entry["time"])
                if key not in seen:
                    seen.add(key)
                    if entry["time"] >= started:
                        require(
                            label + "_no_false_enforcement",
                            entry["action"] == "observe",
                        )
                        require(
                            label + "_no_robotic_pathing",
                            entry["module"] != "pathingmonitor",
                        )
        time.sleep(1)
    phases.append(
        {
            "phase": label,
            "samples": len(samples),
            "max_ping": max(
                (p["ping"] for s in samples for p in s["players"]), default=0
            ),
            "healthy_samples": sum(
                any(p["ready"] for p in s["players"]) for s in samples
            ),
            "guarded_samples": sum(
                any(not p["ready"] for p in s["players"]) for s in samples
            ),
        }
    )
    return samples


def healthy(samples):
    return any(
        len(s["players"]) == 2 and all(p["ready"] for p in s["players"])
        for s in samples
    )


def guard(samples):
    return any(any(not p["ready"] for p in s["players"]) for s in samples)


candidate = status()
plugin_hash = server_python(
    "import hashlib,json;from pathlib import Path;"
    f"p=Path({args.server_path!r})/'plugins'/"
    f"{'endstone_paradox.so' if args.server_container else 'endstone_paradox.dll'!r};"
    "print(json.dumps(hashlib.sha256(p.read_bytes()).hexdigest()))"
)
netem("delay", "30ms")
relative = client_control.relative_to(root).as_posix()
client_command = [
    "docker",
    "exec",
    args.client_container,
    args.client_binary,
] + [
    "--transport",
    args.transport,
    "--address",
    args.address,
    "--control",
    "/work/" + relative,
    "--duration",
    "20m",
]
client = subprocess.Popen(
    client_command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
)


def read():
    with (out / "client.log").open("w", encoding="utf-8") as log:
        for line in client.stdout:
            log.write(line)
            log.flush()
            try:
                events.append(json.loads(line))
            except ValueError:
                pass


threading.Thread(target=read, daemon=True).start()
failure = None
try:
    until = time.monotonic() + 90
    while time.monotonic() < until:
        if sum(e.get("event") == "spawn" for e in events) == 2:
            break
        if client.poll() is not None:
            raise RuntimeError("Client failed; inspect client.log")
        time.sleep(0.25)
    require(
        "two_protocol_2193_clients_spawned",
        sum(
            e.get("event") == "spawn" and e["value"]["protocol"] == 2193 for e in events
        )
        == 2,
    )
    console("tp ParadoxTestA 0.25 301 0.75")
    console("tp ParadoxTestB 3.25 301 0.75")
    baseline = monitor("healthy_join_and_idle", 25)
    require("healthy_detection_reached", healthy(baseline))
    require("no_premature_afk", not any("You are AFK" in str(e) for e in events))
    action(action="command", value="/ac-mode logonly")
    action(action="command", value="/ac-home set base")
    monitor("ordinary_player_permissions", 8)
    require("staff_command_denied", status()["mode"] == "hard")
    users = {p["name"]: p["uuid"] for p in status()["players"]}
    home = table("homes").get(users["ParadoxTestA"], {}).get("base", {})
    require(
        "home_preserves_fractional_coordinates",
        abs(home.get("x", 999) - 0.25) < 0.01 and abs(home.get("z", 999) - 0.75) < 0.01,
    )
    action(action="walk", value="on")
    walking = monitor("normal_walking", 65)
    require("walking_detection_active", healthy(walking))
    positions = [
        e["value"]["position"]
        for e in events
        if e.get("name") == "ParadoxTestA" and e.get("event") == "state"
    ]
    require(
        "client_actually_walked",
        bool(positions)
        and max(p[2] for p in positions) - min(p[2] for p in positions) > 10,
    )
    for slot in range(9):
        action(action="hotbar", slot=slot)
    monitor("valid_hotbar_slots", 5)
    netem("delay", "300ms", "100ms", "distribution", "normal", "loss", "3%")
    lag = monitor("high_latency_jitter_loss", 45)
    require("lag_guard_activated", guard(lag))
    netem("delay", "30ms")
    recovered = monitor("network_recovery", 30)
    require("detection_resumed_after_lag", healthy(recovered))
    netem("delay", "30ms", "loss", "100%")
    time.sleep(3)
    netem("delay", "30ms")
    burst = monitor("outage_and_buffered_recovery", 30)
    require("outage_guard_activated", guard(burst))
    require("outage_recovered", healthy(burst))
    if args.server_container:
        pid = json.loads((out / "ready.json").read_text())["pid"]
        executable = run(
            "docker", "exec", args.server_container, "readlink", f"/proc/{pid}/exe"
        ).strip()
        require(
            "stall_targets_owned_bds",
            executable == args.server_path + "/bedrock_server",
        )
        run("docker", "exec", args.server_container, "kill", "-STOP", str(pid))
        try:
            time.sleep(2)
        finally:
            run("docker", "exec", args.server_container, "kill", "-CONT", str(pid))
        stall = monitor("server_stall_recovery", 30)
        require("server_stall_guard_activated", guard(stall))
        require("server_stall_recovered", healthy(stall))
    console("tp ParadoxTestA 20.25 301 20.75")
    teleport = monitor("teleport_recovery", 25)
    require("teleport_guard_activated", guard(teleport))
    require("teleport_recovered", healthy(teleport))
    console("effect ParadoxTestA speed 5 1 true")
    effect = monitor("effect_recovery", 25)
    require("effect_guard_activated", guard(effect))
    require("effect_recovered", healthy(effect))
    action(action="walk", value="off")
    home_events = len(events)
    action(action="command", value="/ac-home tp base")
    monitor("home_return", 20)
    require(
        "home_return_reached_saved_position",
        any(
            e.get("name") == "ParadoxTestA"
            and e.get("event") == "move"
            and abs(e["value"][0] - 0.25) < 0.01
            and abs(e["value"][2] - 0.75) < 0.01
            for e in events[home_events:]
        ),
    )
    console("tp ParadoxTestA 0.25 301 0.75")
    console("tp ParadoxTestB 2.25 301 0.75")
    action(action="hotbar", slot=0)
    action(action="look", value="-90")
    monitor("melee_setup", 20)
    combat_events = len(events)
    for _ in range(4):
        action(action="attack", value="ParadoxTestB")
        monitor("legitimate_melee", 2)
    require(
        "melee_reached_server",
        any(
            e.get("name") == "ParadoxTestB"
            and e.get("event") == "attributes"
            and any(
                a.get("Name") == "minecraft:health" and a.get("Value", 20) < 20
                for a in e["value"]
            )
            for e in events[combat_events:]
        ),
    )
    action(name="ParadoxTestB", action="command", value="/ac-pvp off")
    monitor("combat_policy", 3)
    require(
        "combat_toggle_rejected",
        table("pvp_data").get(users["ParadoxTestB"], True) is not False,
    )
    action(action="command", value="/ac-gui")
    monitor("native_gui", 3)
    require("native_form_delivered", any(e.get("event") == "form" for e in events))
    # Real malformed-slot cancellation is a positive control, not a legitimate-client scenario.
    positive_start = time.time()
    action(action="hotbar", slot=9)
    monitor("invalid_hotbar_positive_control", 4, enforce_clean=False)
    require(
        "invalid_hotbar_cancelled",
        any(
            e["time"] >= positive_start
            and e["module"] == "hotbarcheck"
            and e["action"] == "cancel"
            for e in status()["evidence"]
        ),
    )
    require("invalid_slot_did_not_kick", len(status()["players"]) == 2)
    # Keep transport at 20 packets/s and advance the clock at 30 ticks/s.
    # Sending 30 packets/s makes BDS process same-tick batches, correctly invoking
    # the burst guard; that cannot serve as a healthy-clock positive control.
    action(action="clock", rate=30)
    until = time.monotonic() + 80
    detected = False
    while time.monotonic() < until:
        s = status()
        with (out / "network-samples.ndjson").open("a") as f:
            f.write(
                json.dumps({"phase": "accelerated_clock", "time": time.time(), **s})
                + "\n"
            )
        if any(
            e["time"] >= positive_start
            and e["module"] == "timer"
            and e["action"] != "observe"
            for e in s["evidence"]
        ):
            detected = True
            break
        time.sleep(1)
    require("accelerated_client_positive_control", detected)
    action(action="clock", rate=20)
    console("ac-setclearance ParadoxTestA 4")
    time.sleep(2)
    action(action="command", value="/ac-modstate fly off")
    time.sleep(3)
    require(
        "explicit_staff_clearance_authorized",
        status()["modules"]["fly"]["enabled"] is False,
    )
    console("ac-modstate fly on")
    console("ac-setclearance ParadoxTestA 1")
    require(
        "no_unexpected_runtime_errors",
        not any(
            x in (out / "server.log").read_text()
            for x in (
                "Event inspection suspended:",
                "Paradox tick:",
                "Paradox startup failed:",
            )
        ),
    )
except Exception as e:
    failure = str(e)
    print("FAILED:", failure, flush=True)
finally:
    action(action="stop")
    try:
        client.wait(timeout=15)
    except subprocess.TimeoutExpired:
        client.terminate()
        client.wait(timeout=10)
    netem("delay", "30ms")
    report = {
        "started": started,
        "finished": time.time(),
        "transport": args.transport,
        "server_platform": "linux" if args.server_container else "windows",
        "retail_client": False,
        "network_impairment": True,
        "client_library": "gophertunnel v1.62.0 / protocol 2193",
        "plugin_version": candidate["version"],
        "plugin_sha256": plugin_hash,
        "accelerated_clock_transport_packets_per_second": 20,
        "accelerated_clock_ticks_per_second": 30,
        "checks": checks,
        "phases": phases,
        "failure": failure,
    }
    (out / "network-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
if failure:
    raise SystemExit(1)
