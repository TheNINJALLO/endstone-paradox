# Architecture

## Project Structure

```
endstone-paradox/
├── pyproject.toml              # Build configuration (hatchling)
├── README.md
├── docs/                       # This documentation site
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py              # Main plugin (31 commands, event handlers)
    ├── database.py             # SQLite persistence (WAL mode)
    ├── security.py             # 4-level clearance + SHA-256 auth
    ├── config.py               # TOML config loader
    ├── globalban.py            # 509 known cheaters from original Paradox
    ├── modules/                # 20 detection & admin modules
    │   ├── base.py             #   Abstract base class + sensitivity
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
    │   └── invsync.py          #   Inventory sync
    ├── commands/
    │   ├── moderation/         # 18 admin/moderation commands
    │   ├── settings/           # Module toggle handler
    │   └── utility/            # 9 utility commands
    ├── gui/
    │   └── form_generator.py   # Full GUI (8 sections)
    └── web/
        └── server.py           # Flask web server + all routes + templates
```

## Design Patterns

### BaseModule Pattern
All 20 modules extend `BaseModule`, which provides:
- **Lifecycle management**: `start()`, `stop()`, `on_start()`, `on_stop()`
- **Periodic checks**: Scheduler-based `check()` method at configurable intervals
- **Sensitivity scaling**: `_scale()` method for threshold adjustment
- **Event hooks**: `on_player_join()`, `on_player_leave()`, `on_damage()`, `on_block_break()`, `on_block_place()`, `on_packet()`
- **Admin alerts**: `alert_admins()` broadcasts to L4 players

### Event Routing
The main `paradox.py` registers for Endstone events and routes them to the appropriate modules:
- `on_player_join` → module `on_player_join` (invsync)
- `on_player_quit` → module `on_player_leave` (all modules)
- `on_actor_damage` → killaura, reach, autoclicker, pvp, selfinfliction
- `on_block_break` → xray
- `on_block_place` → scaffold, antidupe
- `on_packet_receive` → ratelimit, packetmonitor, antidupe

### Database Design
Uses SQLite in **WAL mode** for concurrent read/write. Data is stored as JSON-serialized values in key-value tables, providing flexibility without schema migrations.
