# Architecture

## Project Structure

```
endstone-paradox/
├── pyproject.toml              # Build configuration (hatchling)
├── README.md
├── docs/                       # This documentation site
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py              # Main plugin (35 commands, event handlers)
    ├── database.py             # SQLite persistence (WAL mode)
    ├── security.py             # 4-level clearance + SHA-256 auth
    ├── config.py               # TOML config loader
    ├── globalban.py            # 509 known cheaters from original Paradox
    ├── core/                   # Core engine components
    │   └── violation_engine.py #   Centralized violation processing
    ├── modules/                # 21 detection & admin modules
    │   ├── base.py             #   Abstract base class + sensitivity + emit()
    │   ├── fly.py              #   Flight/hover detection
    │   ├── killaura.py         #   Combat bot detection
    │   ├── reach.py            #   Reach hack (Catmull-Rom)
    │   ├── autoclicker.py      #   CPS tracking
    │   ├── scaffold.py         #   Speed bridge detection
    │   ├── xray.py             #   X-ray (weighted suspicion)
    │   ├── gamemode.py         #   Gamemode change blocking
    │   ├── namespoof.py        #   Name validation
    │   ├── self_infliction.py  #   Self-damage detection
    │   ├── afk.py              #   AFK idle tracking
    │   ├── vision.py           #   Aimbot detection
    │   ├── world_border.py     #   Border enforcement
    │   ├── lag_clear.py        #   Entity cleanup
    │   ├── rate_limit.py       #   Packet flood detection
    │   ├── packet_monitor.py   #   Packet spam alerts
    │   ├── pvp_manager.py      #   PvP toggle system
    │   ├── containersee.py     #   Container vision (admin)
    │   ├── antidupe.py         #   4-layer dupe prevention
    │   ├── crashdrop.py        #   Anti-crash-drop
    │   ├── invsync.py          #   Inventory sync
    │   └── skinguard.py        #   4D/tiny/invisible skin detection
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
All 21 modules extend `BaseModule`, which provides:
- **Lifecycle management**: `start()`, `stop()`, `on_start()`, `on_stop()`
- **Periodic checks**: Scheduler-based `check()` method at configurable intervals
- **Sensitivity scaling**: `_scale()` method for threshold adjustment
- **Event hooks**: `on_player_join()`, `on_player_leave()`, `on_damage()`, `on_move()`, `on_block_break()`, `on_block_place()`, `on_packet()`
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

### Player Baseline (EMA Profiling)
Each player builds a **behavioral baseline** via Exponential Moving Averages. Modules record metrics (hit distance, attack rate, hover time, ore ratio, etc.) during normal play. The `PlayerBaseline` class tracks rolling averages and variance per metric, then detects statistical deviations (z-score > 2.5σ). First 30 samples per metric are warmup (no false positives). Saves to `baselines` table in DB across sessions.

Modules use **dual-layer detection**: fixed threshold catches obvious cheats, baseline deviation catches subtle behavior shifts (e.g., a player whose reach distance suddenly increases by 2 blocks).

### Event Routing
The main `paradox.py` registers for Endstone events and routes them to the appropriate modules:
- `on_player_join` → global API ban check, namespoof check, skinguard check, baseline load, module `on_player_join` (invsync)
- `on_player_quit` → module `on_player_leave` (all modules) + violation engine cleanup + baseline flush
- `on_actor_damage` → killaura (multi-target + baselines), reach, autoclicker (click_rate baseline), pvp, selfinfliction, fly (knockback tracking), vision (pre-attack snap)
- `on_block_break` → xray
- `on_block_place` → scaffold (backwards detection + baseline), antidupe
- `on_packet_receive` → ratelimit, packetmonitor (emits violations), antidupe, autoclicker

### Database Design
Uses SQLite in **WAL mode** for concurrent read/write. Data is stored as JSON-serialized values in key-value tables, providing flexibility without schema migrations. The `violations` table stores enforcement evidence with write-behind buffering for performance. The `baselines` table stores per-player EMA profiles (rolling averages, variance, sample counts).
