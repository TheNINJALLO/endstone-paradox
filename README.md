# Paradox AntiCheat

A comprehensive anti-cheat and server moderation plugin for **Endstone** (Minecraft Bedrock Edition).

Paradox provides 16 detection modules, 42+ admin commands, a GUI management interface, and a persistent SQLite-backed configuration system — all running as a native Endstone Python plugin.

> **Originally created by [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat)**
> Ported to Endstone by **TheN1NJ4LL0**

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

All modules can be individually toggled with `/ac-<module>` commands and configured through the GUI.

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

### 🖥️ GUI System

`/ac-gui` opens an interactive ActionForm/ModalForm interface with:
- Module toggles (enable/disable any module)
- Player management (kick, ban, freeze, warn, teleport)
- Security dashboard (clearance levels, lockdown status)
- Server settings editor (AFK timeout, lag clear interval, max CPS)
- Database browser (table viewer, key inspector)

---

## Commands

### Moderation (Operator)

| Command | Description |
|---------|-------------|
| `/ac-op <password>` | Grant Level 4 clearance |
| `/ac-deop [player]` | Revoke clearance |
| `/ac-ban <player> [reason]` | Ban a player |
| `/ac-unban <name>` | Unban a player |
| `/ac-kick <player> [reason]` | Kick a player |
| `/ac-freeze <player>` | Freeze/unfreeze a player |
| `/ac-vanish` | Toggle admin invisibility |
| `/ac-lockdown` | Toggle server lockdown |
| `/ac-punish <player> <action>` | Punish (warn/kick/tempban/ban/smite) |
| `/ac-tpa <player\|accept\|deny>` | Teleport request system |
| `/ac-allowlist <add\|remove\|list>` | Manage allow list |
| `/ac-whitelist <add\|remove\|list>` | Manage whitelist |
| `/ac-opsec` | Security dashboard |
| `/ac-despawn [type] [radius]` | Remove entities |
| `/ac-modules` | Module status dashboard |
| `/ac-spooflog` | View namespoof logs |
| `/ac-command <enable\|disable> <cmd>` | Enable/disable commands |
| `/ac-prefix [prefix]` | Change display prefix |

### Settings (Operator)

| Command | Description |
|---------|-------------|
| `/ac-fly` | Toggle fly detection |
| `/ac-killaura` | Toggle killaura detection |
| `/ac-reach` | Toggle reach detection |
| `/ac-autoclicker [maxcps]` | Toggle/configure autoclicker detection |
| `/ac-scaffold` | Toggle scaffold detection |
| `/ac-xray` | Toggle xray detection |
| `/ac-gamemode` | Toggle gamemode detection |
| `/ac-afk [timeout]` | Toggle/configure AFK detection |
| `/ac-vision` | Toggle vision detection |
| `/ac-worldborder [radius] [x] [z]` | Configure world border |
| `/ac-lagclear [interval]` | Toggle/configure lag clear |
| `/ac-ratelimit` | Toggle rate limiting |
| `/ac-namespoof` | Toggle namespoof detection |
| `/ac-packetmonitor` | Toggle packet monitor |

### Utility (All Players)

| Command | Description |
|---------|-------------|
| `/ac-home [set\|delete\|list] [name]` | Home locations (max 5) |
| `/ac-tpr [radius]` | Random teleport |
| `/ac-pvp [global]` | Toggle PvP |
| `/ac-channels <action> [name] [msg]` | Private chat channels |
| `/ac-tpa <player>` | Teleport requests |

### Utility (Operator)

| Command | Description |
|---------|-------------|
| `/ac-invsee <player>` | View player inventory |
| `/ac-rank <player> [rank]` | Set player rank |
| `/ac-debug-db [table] [key] [value]` | SQLite database inspector |
| `/ac-gui` | Open admin GUI |

---

## Installation

### Requirements

- **Endstone** server v0.11+
- **Python** 3.9+

### From Wheel

```bash
# Build the wheel
cd endstone-paradox
pip install build
python -m build --wheel

# Install on server
pip install dist/endstone_paradox-1.0.0-py3-none-any.whl
```

Or copy the `.whl` file directly to your server's `plugins/` folder.

### From Source

```bash
pip install -e .
```

---

## Configuration

All settings are stored in and managed through the SQLite database at `plugins/ParadoxAC/paradox.db`. Use `/ac-debug-db` or `/ac-gui` → **Server Settings** to adjust values.

### Key Config Values

| Setting | Default | Description |
|---------|---------|-------------|
| `afk_timeout` | 600 | Seconds before AFK kick |
| `lagclear_interval` | 300 | Seconds between lag clears |
| `max_cps` | 20 | Maximum clicks per second |
| `worldborder.radius` | 10000 | World border radius |
| `global_pvp` | true | Global PvP toggle |

---

## Architecture

```
endstone-paradox/
├── pyproject.toml
├── README.md
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py          # Main plugin entry point
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
    │   └── utility/        # 8 utility commands
    └── gui/
        └── form_generator.py  # ActionForm/ModalForm menus
```

---

## License

MIT
