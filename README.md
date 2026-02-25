# Paradox AntiCheat

A comprehensive anti-cheat and server moderation plugin for **Endstone** (Minecraft Bedrock Edition).

Paradox provides 16 detection modules, 31 admin commands, a full GUI management interface, and a persistent SQLite-backed configuration system — all running as a native Endstone Python plugin.

> **Originally created by [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat)**
> Ported to Endstone by **TheN1NJ4LL0**

📦 **GitHub:** [https://github.com/TheN1NJ4LL0/endstone-paradox](https://github.com/TheN1NJ4LL0/endstone-paradox)
📥 **Download:** [Latest Release](https://github.com/TheN1NJ4LL0/endstone-paradox/releases/latest)

This is a full Python port of the original [Paradox AntiCheat](https://github.com/Visual1mpact/Paradox_AntiCheat) for Minecraft Bedrock Edition, rebuilt from the ground up as a native Endstone plugin with SQLite persistence, SHA-256 authentication, and protocol-level detection.

---

## Features

### 🛡️ Anti-Cheat Detection Modules

| Module | Description |
|--------|-------------|
| **Fly** | Ground tracking, velocity analysis, trident exemption |
| **KillAura** | Attack timing statistics, facing angle validation |
| **Reach** | Movement interpolation, distance analysis |
| **AutoClicker** | Sliding-window CPS tracking (configurable max) |
| **Scaffold** | Rapid block placement + axis pattern detection |
| **X-Ray** | Per-ore mining rate thresholds with admin alerts |
| **GameMode** | Unauthorized gamemode change blocking |
| **Namespoof** | Name length, character, and duplicate validation |
| **Self-Infliction** | Self-damage exploit detection |
| **AFK** | Position-based idle detection with kick + warnings |
| **Vision** | Rotation snap-count analysis for aimbot detection |
| **World Border** | Configurable radius enforcement with teleport-back |
| **Rate Limiter** | Packet flood detection with automatic DoS lockdown |
| **Packet Monitor** | Per-type frequency monitoring and spam alerts |
| **PvP Manager** | Per-player toggles, combat tagging, combat log detection |
| **Lag Clear** | Scheduled entity cleanup with 30-second warnings |

All modules can be individually toggled with `/ac-<module>` commands and managed through the GUI.

### 🔐 Security System

- **4-level clearance system** — Level 1 (default) through Level 4 (full admin)
- **SHA-256 password hashing** — First `/ac-op` sets the password; subsequent uses verify it
- **Level 4 exemptions** — Admins are exempt from all detection modules
- **Admin notifications** — All security events broadcast to Level 4 players

### 💾 Persistence

All data is stored in **SQLite** with WAL mode for concurrent access:
- Bans, allowlists, and whitelists
- Module enable/disable states
- Player homes, ranks, and channels
- Frozen/vanished player lists
- Namespoof logs
- Configuration settings

### 🖥️ Full GUI System

`/ac-gui` opens a complete admin panel with **8 sections** — every single command and feature is accessible from the GUI:

| Section | What You Can Do |
|---------|----------------|
| **Modules** | Toggle all 14 detection modules on/off with a single tap |
| **Moderation** | Vanish, lockdown, kick, ban, unban, freeze, punish (warn/mute/kick/ban), despawn entities, allowlist, whitelist, spoof log, change prefix |
| **Players** | Select any online player → kick, ban, freeze, warn, teleport to/from, set rank, view inventory |
| **Utilities** | Homes (set/delete/update/teleport), random TP, PvP toggle (personal + global), chat channels (create/join/leave/send), TPA, ranks, about |
| **Security** | Dashboard showing lockdown, frozen, vanished, banned counts + opsec report |
| **Settings** | Lockdown, AFK timeout, lagclear interval, max CPS, world border radius, global PvP — all in one form |
| **Commands** | Enable/disable any of the 31 Paradox commands |
| **Database** | Browse and inspect all database tables |

---

## Commands

### Moderation

| Command | Description |
|---------|-------------|
| `/ac-op [password]` | Authenticate with password to gain security clearance |
| `/ac-deop [player]` | Revoke your or another player's security clearance |
| `/ac-ban <player> [reason]` | Ban a player with an optional reason |
| `/ac-unban <name>` | Unban a player by name |
| `/ac-kick <player> [reason]` | Kick a player from the server with an optional reason |
| `/ac-freeze <player>` | Freeze or unfreeze a player in place |
| `/ac-vanish` | Toggle invisibility — hide from all players |
| `/ac-lockdown` | Toggle server lockdown — only Level 4 can use commands |
| `/ac-punish <player> [action]` | Punish a player (warn/mute/kick/ban) |
| `/ac-tpa <player>` | Send a teleport request to another player |
| `/ac-allowlist [args]` | Manage allow list: add/remove/list players |
| `/ac-whitelist [args]` | Manage whitelist: add/remove/list players |
| `/ac-opsec` | View security dashboard with admin clearance levels |
| `/ac-despawn [type] [radius]` | Despawn entities by type within radius |
| `/ac-modules` | View all detection modules and their on/off status |
| `/ac-spooflog` | View log of detected name spoofing attempts |
| `/ac-command [args]` | Enable or disable a Paradox command |
| `/ac-prefix [prefix]` | Change the Paradox chat prefix display |

### Detection Toggles

| Command | Description |
|---------|-------------|
| `/ac-fly` | Toggle fly/hover hack detection on or off |
| `/ac-killaura` | Toggle kill aura detection on or off |
| `/ac-reach` | Toggle reach hack detection on or off |
| `/ac-autoclicker [maxcps]` | Toggle autoclicker detection, optionally set max CPS |
| `/ac-scaffold` | Toggle scaffold/fast-bridge detection on or off |
| `/ac-xray` | Toggle X-ray mining detection on or off |
| `/ac-gamemode` | Toggle illegal gamemode change detection on or off |
| `/ac-afk [timeout]` | Toggle AFK detection, optionally set timeout in seconds |
| `/ac-vision` | Toggle aimbot/snap detection on or off |
| `/ac-worldborder [args]` | Set world border radius and center position |
| `/ac-lagclear [interval]` | Toggle periodic entity clearing, optionally set interval |
| `/ac-ratelimit` | Toggle packet rate limiting on or off |
| `/ac-namespoof` | Toggle name spoofing detection on or off |
| `/ac-packetmonitor` | Toggle packet spam monitoring on or off |

### Utility

| Command | Description |
|---------|-------------|
| `/ac-home [args]` | Manage homes: set/delete/list or teleport by name (max 5) |
| `/ac-tpr [radius]` | Teleport to a random location, optionally set radius |
| `/ac-pvp [args]` | Toggle PvP: use alone or with global/status/help |
| `/ac-channels [args]` | Private chat: create/join/leave/list/send channels |
| `/ac-invsee <player>` | View another player's inventory contents |
| `/ac-rank <player> [rank]` | Set or view a player's display rank |
| `/ac-debug-db [args]` | Inspect or modify the Paradox database directly |
| `/ac-gui` | Open the Paradox admin GUI menu |
| `/ac-about` | View Paradox AntiCheat version and info |

---

## Installation

### Requirements

- **Endstone** server v0.11+
- **Python** 3.9+

### From Release (Recommended)

1. Download `endstone_paradox-1.0.0-py3-none-any.whl` from the [Releases page](https://github.com/TheN1NJ4LL0/endstone-paradox/releases/latest)
2. Drop the `.whl` file into your Endstone server's `plugins/` folder
3. Restart the server

### From Source

```bash
git clone https://github.com/TheN1NJ4LL0/endstone-paradox.git
cd endstone-paradox
pip install build
python -m build --wheel
# Copy dist/endstone_paradox-1.0.0-py3-none-any.whl to your server's plugins/ folder
```

---

## Configuration

All settings are stored in and managed through the SQLite database at `plugins/ParadoxAC/paradox.db`. Use `/ac-debug-db`, `/ac-gui` → **Settings**, or the individual commands to adjust values.

### Key Config Values

| Setting | Default | Description |
|---------|---------|-------------|
| `afk_timeout` | 600 | Seconds before AFK kick |
| `lagclear_interval` | 300 | Seconds between lag clears |
| `max_cps` | 20 | Maximum clicks per second |
| `worldborder_radius` | 10000 | World border radius |
| `global_pvp` | true | Global PvP toggle |

---

## Architecture

```
endstone-paradox/
├── pyproject.toml
├── README.md
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py          # Main plugin entry point (31 commands)
    ├── database.py         # SQLite persistence layer
    ├── security.py         # 4-level clearance system
    ├── modules/            # 16 detection modules
    │   ├── base.py         # Abstract base class
    │   ├── fly.py
    │   ├── killaura.py
    │   ├── reach.py
    │   ├── autoclicker.py
    │   ├── scaffold.py
    │   ├── xray.py
    │   ├── gamemode.py
    │   ├── namespoof.py
    │   ├── self_infliction.py
    │   ├── afk.py
    │   ├── vision.py
    │   ├── world_border.py
    │   ├── lag_clear.py
    │   ├── rate_limit.py
    │   ├── packet_monitor.py
    │   └── pvp_manager.py
    ├── commands/
    │   ├── moderation/     # 18 admin commands
    │   ├── settings/       # Module toggle handler
    │   └── utility/        # 9 utility commands
    └── gui/
        └── form_generator.py  # Full GUI (700+ lines, 8 sections)
```

---

## License

MIT
