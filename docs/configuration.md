# Configuration

## Overview

Paradox uses a **TOML configuration file** located in the plugin's data folder:

```
server/plugins/endstone-paradox/config.toml
```

## Configuration Sections

### Database
```toml
[database]
mode = "sqlite"     # SQLite with WAL mode
```

### Web UI
```toml
[web_ui]
enabled = true
port = 8005
secret = "change-this-secret-key"
admin_hash = ""     # SHA-256 hash of admin password (auto-set)
```

### Global Database
```toml
[global_database]
enabled = true      # Enable global ban list checking
```

### Modules
Module states and sensitivity values are stored in the **SQLite database**, not the config file. This ensures they persist independently and can be modified at runtime via commands, GUI, or web UI.

## Runtime Configuration

Most settings can be changed at runtime without restarting the server:
- **Module toggles**: `/ac-modules <name> <on/off>`
- **Sensitivity**: `/ac-modules <name> sensitivity <1-10>`
- **Lockdown**: `/ac-lockdown`
- **Web UI config**: Edit via the Config page

## Data Storage

All runtime data is stored in SQLite (WAL mode) at:
```
server/plugins/endstone-paradox/paradox.db
```

Tables include:
- `modules` — Module enabled states and sensitivity values
- `bans` — Server ban list
- `players` — Player records, clearance levels, join times
- `frozen_players` — Currently frozen players
- `vanished_players` — Currently vanished players
- `homes` — Player home points
- `inv_snapshots` — Inventory sync snapshots
- `antidupe_log` — Anti-dupe detection events
- `crashdrop_log` — Crash-drop detection events
- `invsync_log` — Inventory sync detection events
