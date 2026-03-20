# Web Admin Panel

## Overview

Paradox includes a built-in **Flask-based web admin panel** that runs alongside your server. It provides a full-featured dashboard for remote server management.

## Accessing the Web UI

The web UI starts automatically on port **8080**:

```
http://your-server-ip:8080
```

### Authentication
Login with the secret key configured in `config.toml`:
```toml
[web_ui]
enabled = true
port = 8080
host = "0.0.0.0"
secret_key = "your-secret-key"
```

## Pages

### Dashboard
Overview of your server including:
- Total modules, ban count, player count
- Frozen/vanished player counts
- Lockdown status
- Module status summary

### Modules
Toggle all 39 modules on/off and adjust sensitivity (1-10) per module.

### Bans
- View all server bans
- Add/remove bans
- View global ban list (509 known cheaters)
- Search across all ban entries

### Players
View all known players with their:
- UUID
- Name
- Last join time
- Clearance level

### Permissions
Set clearance levels (L1-L4) for any player directly from the web UI.

### Anti-Dupe Monitor
Dedicated monitoring page for duplication exploits:
- **Dupe Detection Events**: Hopper clusters, piston anomalies, rapid inventory transactions, container access patterns
- **Crash-Drop Events**: Disconnect tracking, removed items, rapid disconnect patterns
- **Inventory Sync Events**: Rejoin inventory anomalies
- Searchable/filterable event log

### Logs
View recent server and module logs.

### Config
Edit TOML configuration values directly from the web UI.

### Allow/Whitelist
Manage server allowlist and whitelist entries.

### Global DB
View and manage global ban database entries.

### Violations
Per-player violation history and evidence browser:
- **Violation list**: All players with violations sorted by count, showing severity badge, modules flagged, and last violation time
- **Player detail**: Full violation timeline with severity filters (Critical/High/Medium/Low/Info)
- **Descriptions**: Each violation shows a human-readable description explaining what triggered the detection
- **Evidence grid**: Raw evidence key-value pairs for each violation
- **Clear**: Clear violations per-player or globally
