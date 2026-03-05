# Architecture

## Project Structure

```
endstone-paradox/
├── pyproject.toml              # Build configuration (hatchling)
├── README.md
├── docs/                       # This documentation site
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py              # Main plugin (35+ commands, event handlers)
    ├── database.py             # SQLite persistence (WAL mode)
    ├── security.py             # 4-level clearance + SHA-256 auth
    ├── config.py               # TOML config loader
    ├── globalban.py            # 509 known cheaters from original Paradox
    ├── core/                   # Core engine components
    │   ├── violation_engine.py #   Centralized violation processing
    │   └── player_baseline.py  #   EMA behavioral profiling per player
    ├── modules/                # 35 detection, community & admin modules
    │   ├── base.py             #   Abstract base class + sensitivity + emit()
    │   ├── # Movement Detection (Tier 1)
    │   ├── fly.py              #   Flight/hover (surrounding-block, velocity analysis)
    │   ├── noclip.py           #   Phase through solid blocks (ray-trace)
    │   ├── waterwalk.py        #   Jesus hack (Frost Walker/ice/lily exemptions)
    │   ├── stephack.py         #   Step up blocks without jumping
    │   ├── timer.py            #   Game speed manipulation (packet frequency)
    │   ├── blink.py            #   Instant teleport/position jumps
    │   ├── # Combat Detection (Tier 1)
    │   ├── killaura.py         #   Combat bot (dynamic thresholds, multi-target)
    │   ├── reach.py            #   Reach hack (Catmull-Rom interpolation)
    │   ├── autoclicker.py      #   CPS tracking (PC/Mobile/Console)
    │   ├── antikb.py           #   Anti-knockback (post-hit displacement)
    │   ├── criticals.py        #   Always-critical hit exploits
    │   ├── wallhit.py          #   Hitting through solid blocks (LoS ray-trace)
    │   ├── triggerbot.py       #   Auto-attack on target acquisition
    │   ├── vision.py           #   Aimbot/snap aim detection
    │   ├── # Other Detection
    │   ├── scaffold.py         #   Speed bridge (air-below, backwards placement)
    │   ├── xray.py             #   X-ray (weighted suspicion scoring)
    │   ├── gamemode.py         #   Gamemode change blocking
    │   ├── namespoof.py        #   Name validation
    │   ├── self_infliction.py  #   Self-damage detection
    │   ├── skinguard.py        #   4D/tiny/invisible skin detection
    │   ├── illegal_items.py    #   Illegal item scanner (enchants, stacks)
    │   ├── # Community & Moderation (Tier 2)
    │   ├── discord_webhook.py  #   Discord webhook integration (violations, bans, kicks)
    │   ├── chat_protection.py  #   Spam/ad/swear filter + mute system
    │   ├── antigrief.py        #   Anti-nuke, rapid placement, explosion logging
    │   ├── evidence_replay.py  #   Ring-buffer recording + violation snapshots
    │   ├── # Prevention
    │   ├── antidupe.py         #   4-layer dupe prevention
    │   ├── crashdrop.py        #   Anti-crash-drop
    │   ├── invsync.py          #   Inventory sync
    │   ├── # Admin & Utility
    │   ├── afk.py              #   AFK idle tracking
    │   ├── world_border.py     #   Border enforcement
    │   ├── lag_clear.py        #   Entity cleanup
    │   ├── rate_limit.py       #   Packet flood detection
    │   ├── packet_monitor.py   #   Packet spam alerts
    │   ├── pvp_manager.py      #   PvP toggle system
    │   └── containersee.py     #   Container/inventory vision (admin)
    ├── commands/
    │   ├── moderation/         # 18 admin/moderation commands
    │   ├── settings/           # Module toggle handler
    │   ├── utility/            # 9 utility commands
    │   └── violation/          # 4 violation engine commands
    ├── gui/
    │   └── form_generator.py   # Full GUI (8 sections)
    └── web/
        └── server.py           # Flask web server + all routes + templates
```

## Design Patterns

### BaseModule Pattern
All 35 modules extend `BaseModule`, which provides:
- **Lifecycle management**: `start()`, `stop()`, `on_start()`, `on_stop()`
- **Periodic checks**: Scheduler-based `check()` method at configurable intervals
- **Sensitivity scaling**: `_scale()` method for threshold adjustment
- **Event hooks**: `on_player_join()`, `on_player_leave()`, `on_damage()`, `on_move()`, `on_block_break()`, `on_block_place()`, `on_packet()`, `on_player_chat()`
- **Violation emission**: `emit(player, severity, evidence, action_hint)` routes to the violation engine
- **Admin alerts**: `alert_admins()` broadcasts to L4 players (fallback)

### Violation Engine
The `ViolationEngine` (in `core/violation_engine.py`) centralizes all enforcement:
- Modules call `self.emit()` instead of punishing directly
- Rolling 5-minute decay buffers per player with severity-weighted scoring
- Cross-module correlation — flags from multiple modules escalate faster
- Enforcement ladder: warn → cancel → setback → kick → ban
- 3 modes: `logonly`, `soft` (default), `hard`
- Rate-limited staff alerts (10s per player per module)
- Write-behind evidence persistence to SQLite (30s flush)
- **Discord webhook integration** — forwards violations, bans, and kicks to Discord

### Player Baseline (EMA Profiling)
Each player builds a **behavioral baseline** via Exponential Moving Averages. Modules record metrics (hit distance, attack rate, hover time, ore ratio, etc.) during normal play. The `PlayerBaseline` class tracks rolling averages and variance per metric, then detects statistical deviations (z-score > 2.5σ). First 30 samples per metric are warmup (no false positives). Saves to `baselines` table in DB across sessions.

Modules use **dual-layer detection**: fixed threshold catches obvious cheats, baseline deviation catches subtle behavior shifts (e.g., a player whose reach distance suddenly increases by 2 blocks).

### Event Routing
The main `paradox.py` registers for Endstone events and routes them to the appropriate modules:
- `on_player_join` → global API ban check, namespoof check, skinguard check, baseline load, module `on_player_join` (invsync)
- `on_player_quit` → module `on_player_leave` (all modules) + violation engine cleanup + baseline flush
- `on_actor_damage` → killaura, reach, autoclicker, antikb, criticals, wallhit, triggerbot, pvp, selfinfliction, fly, vision
- `on_block_break` → xray, antigrief (nuke detection)
- `on_block_place` → scaffold, antidupe, antigrief (rapid placement)
- `on_packet_receive` → ratelimit, packetmonitor, antidupe, autoclicker, timer
- `on_player_chat` → chat_protection (spam, ads, swears, mutes)

### Evidence Replay System
The `EvidenceReplayModule` runs as a background module capturing player state (position, rotation, active actions) in a per-player ring buffer every tick. When any module emits a violation, the replay module snapshots the buffer and persists it to the database. Staff can retrieve and review snapshots to see exactly what happened before and during a violation.

### Database Design
Uses SQLite in **WAL mode** for concurrent read/write. Data is stored as JSON-serialized values in key-value tables, providing flexibility without schema migrations. The `violations` table stores enforcement evidence with write-behind buffering for performance. The `baselines` table stores per-player EMA profiles (rolling averages, variance, sample counts). The `logs` table stores explosion audit trails and evidence replay snapshots.
