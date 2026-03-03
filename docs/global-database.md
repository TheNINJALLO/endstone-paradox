# Global Ban Database

Paradox AntiCheat includes a built-in **cross-server ban system** that automatically shares bans, flags, and violation reports between all servers running the plugin. **No configuration required** — it works out of the box.

## How It Works

```
Server A bans a player
        ↓
    Push to Global Ban API
        ↓
    API stores the ban
        ↓
Server B, C, D... pull the ban on next sync
        ↓
    Player kicked on join attempt
```

### Zero-Config Setup

Every Paradox install automatically:
1. **Connects** to the official Global Ban API on first startup
2. **Self-registers** and receives a unique API key (stored permanently in `config.toml`)
3. **Syncs** bans and flags every 5 minutes
4. **Pushes** local bans and violation reports to the API

Server owners don't need to configure anything — just install the plugin and it joins the global network.

## Player Categories

| Category | What Happens | Example |
|----------|-------------|---------|
| **ban** | Player is kicked on every join attempt across ALL servers | Confirmed cheater |
| **high_risk** | Staff alerted when player joins — player NOT kicked | Known exploiter from another server |
| **flagged** | Staff alerted when player joins — player NOT kicked | Suspicious behavior on another server |

## What Gets Shared

### Bans (auto-push)
When an admin runs `/ac-ban` on any server, the ban is automatically pushed to the global API. **All connected servers will block that player** on their next join attempt.

### Auto-Bans (auto-push)
When the violation engine escalates a player to a ban (e.g., repeated fly/killaura detections), it's also pushed globally.

### Violation Reports (auto-push)
Every violation detected by any module (fly, killaura, reach, xray, etc.) is reported to the API with:
- Player name and XUID
- Module that detected it
- Severity level (1-5)
- Evidence details

This builds a cross-server intelligence profile for each player.

## Join Checks

When a player joins your server, Paradox checks (in order):
1. **Global API bans** — synced entries from the shared database → **kick**
2. **Hardcoded ban list** — 509 known cheaters from original Paradox → **kick**
3. **Local server bans** — your server's ban list → **kick**
4. **Global flags/high-risk** — staff alerted, player NOT kicked

## Configuration

The default `config.toml` is pre-configured to work automatically:

```toml
[global_database]
enabled = true           # On by default
api_url = ""             # Auto-resolved to official API
api_key = ""             # Auto-populated on first connect
server_name = ""         # Defaults to your server's hostname
sync_interval = 300      # Sync every 5 minutes
```

### Disabling

To opt out of the global ban network:
```toml
[global_database]
enabled = false
```

### Self-Hosted

To run your own Global Ban API for a private server network:
```toml
[global_database]
api_url = "http://your-api-server:8090"
```

The plugin will auto-register with your private API instead.

## API Endpoints (for developers)

The Global Ban API is a standalone FastAPI service. Key endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/servers/self-register` | POST | None | Auto-registration (rate-limited) |
| `/api/bans` | POST | API Key | Submit a ban |
| `/api/bans/check/{player}` | GET | API Key | Check if a player is banned |
| `/api/report` | POST | API Key | Submit a violation report |
| `/api/report/batch` | POST | API Key | Batch submit violation reports |
| `/api/sync?since={timestamp}` | GET | API Key | Pull updates since timestamp |
| `/api/flags` | POST | API Key | Flag/high-risk a player |

## Security

- API keys are **SHA-256 hashed** server-side
- Self-registration is **rate-limited** (5 per IP per hour)
- The official API endpoint is **obfuscated** in the plugin source code
- All communication uses standard HTTPS/HTTP
