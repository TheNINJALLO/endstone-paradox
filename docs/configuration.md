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
port = 8080
host = "0.0.0.0"
secret_key = "change-this-secret-key"
```

### Global Database
```toml
[global_database]
enabled = false
api_url = ""               # URL of your Paradox Global Ban API instance
api_key = ""               # Server API key from registration
sync_interval = 300        # Sync every 5 minutes (in seconds)
```

See the standalone [Paradox Global Ban API](https://github.com/TheNINJALLO/endstone-paradox) for setup.

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
- `violations` — Violation engine evidence and enforcement history
- `skin_log` — SkinGuard violation records
- `spoof_log` — NameSpoof detection events
- `antidupe_log` — Anti-dupe detection events
- `crashdrop_log` — Crash-drop detection events
- `invsync_log` — Inventory sync detection events
