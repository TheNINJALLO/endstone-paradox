<p align="center">
  <h1 align="center">🛡️ Paradox AntiCheat</h1>
  <p align="center">
    A comprehensive anti-cheat and server moderation plugin for <strong>Endstone</strong> (Minecraft Bedrock Edition)
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Endstone-v0.11+-00C853?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6TTIgMTdsMTAgNSAxMC01TTIgMTJsMTAgNSAxMC01Ii8+PC9zdmc+&logoColor=white" alt="Endstone v0.11+">
    <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/Minecraft-Bedrock_Edition-62B47A?style=for-the-badge&logo=minecraft&logoColor=white" alt="Minecraft Bedrock">
    <img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge" alt="GPL-3.0 License">
  </p>
  <p align="center">
    <a href="https://github.com/TheNINJALLO/endstone-paradox/releases/latest">
      <img src="https://img.shields.io/github/v/release/TheNINJALLO/endstone-paradox?style=for-the-badge&color=blue&label=Download" alt="Latest Release">
    </a>
    <img src="https://img.shields.io/github/downloads/TheNINJALLO/endstone-paradox/total?style=for-the-badge&color=brightgreen&label=Downloads" alt="Total Downloads">
  </p>
</p>

---

> **Originally created by [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat)**
> — Ported to Endstone by [**TheNINJALLO**](https://github.com/TheNINJALLO)

A full Python port of the original [Paradox AntiCheat](https://github.com/Visual1mpact/Paradox_AntiCheat), rebuilt from the ground up as a native Endstone plugin with SQLite persistence, SHA-256 authentication, protocol-level detection, and a complete in-game GUI.

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Commands](#-commands)
- [GUI System](#-gui-system)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [FAQ](#-faq)
- [License](#-license)

---

## � Quick Start

### Step 1 — Download

Grab the latest `.whl` file from the **[Releases page](https://github.com/TheNINJALLO/endstone-paradox/releases/latest)**.

### Step 2 — Install

Drop the `.whl` file into your Endstone server's `plugins/` folder:

```
your-server/
├── endstone.toml
├── plugins/
│   └── endstone_paradox-1.0.0-py3-none-any.whl   ← drop it here
└── ...
```

### Step 3 — Start the Server

Start (or restart) your Endstone server. You'll see Paradox load in the console:

```
[ParadoxAC] Paradox AntiCheat v1.0.0 loaded!
[ParadoxAC] Database initialized at plugins/ParadoxAC/paradox.db
[ParadoxAC] 14 detection modules registered.
```

### Step 4 — Set Your Admin Password

Join the server and run:

```
/ac-op YourSecretPassword
```

> **⚠️ Important:** The **first time** you run `/ac-op`, the password you type becomes your permanent admin password (hashed with SHA-256). All future `/ac-op` attempts must use this same password.

You now have **Level 4 clearance** — full admin access to all Paradox commands and the GUI.

### Step 5 — Open the GUI

```
/ac-gui
```

This opens the full admin panel where you can manage **everything** — modules, players, moderation, settings, and more — without memorizing any commands.

---

## ✨ Features

### 🛡️ 16 Detection Modules

| Module | What It Detects |
|--------|-----------------|
| **Fly** | Flight/hover hacks — ground tracking, velocity analysis, trident exemption |
| **KillAura** | Combat bots — attack timing, facing angle validation |
| **Reach** | Extended reach hacks — movement interpolation, distance checks |
| **AutoClicker** | Click bots — sliding-window CPS tracking (configurable threshold) |
| **Scaffold** | Speed bridging — rapid block placement + axis pattern analysis |
| **X-Ray** | Mining hacks — per-ore mining rate thresholds with alerts |
| **GameMode** | Unauthorized gamemode changes — instant blocking |
| **Namespoof** | Name manipulation — length, character, and duplicate checks |
| **Self-Infliction** | Self-damage exploits |
| **AFK** | Idle players — position tracking with warnings before kick |
| **Vision** | Aimbot/snap aim — rotation snap-count analysis |
| **World Border** | Border enforcement — configurable radius with teleport-back |
| **Rate Limiter** | Packet floods — automatic DoS lockdown |
| **Packet Monitor** | Packet spam — per-type frequency monitoring |
| **PvP Manager** | PvP system — per-player toggles, combat tagging, log detection |
| **Lag Clear** | Entity cleanup — scheduled clearing with 30-second warnings |

Every module can be toggled individually via commands **or** the GUI.

### 🔐 4-Level Security System

| Level | Name | Access |
|-------|------|--------|
| 1 | Standard | Utility commands (home, tpr, pvp, channels) |
| 2 | Moderator | Player management (kick, freeze, warn) |
| 3 | Admin | Settings and module control |
| 4 | Owner | Full access — all commands, exempt from detection |

- **SHA-256 password hashing** — your password is never stored in plain text
- **Security broadcasts** — all admin actions are reported to Level 4 players
- **Lockdown mode** — restrict all commands to Level 4 only

### 💾 SQLite Persistence

Everything saves automatically and survives server restarts:

- Bans, allowlists, whitelists
- Module states (enabled/disabled)
- Player homes, ranks, channels
- Frozen/vanished player lists
- Namespoof detection logs
- All configuration settings

---

## 📖 Commands

### Moderation

| Command | Description |
|---------|-------------|
| `/ac-op [password]` | Authenticate to gain security clearance |
| `/ac-deop [player]` | Revoke your or another player's clearance |
| `/ac-ban <player> [reason]` | Ban a player with an optional reason |
| `/ac-unban <name>` | Unban a player by name |
| `/ac-kick <player> [reason]` | Kick a player with an optional reason |
| `/ac-freeze <player>` | Freeze or unfreeze a player in place |
| `/ac-vanish` | Toggle invisibility — hide from all players |
| `/ac-lockdown` | Toggle server lockdown (Level 4 only) |
| `/ac-punish <player> [action]` | Punish a player (warn/mute/kick/ban) |
| `/ac-tpa <player>` | Send a teleport request |
| `/ac-allowlist [add\|remove\|list]` | Manage the allow list |
| `/ac-whitelist [add\|remove\|list]` | Manage the whitelist |
| `/ac-opsec` | View security dashboard |
| `/ac-despawn [type] [radius]` | Despawn entities by type within radius |
| `/ac-modules` | View all modules and their status |
| `/ac-spooflog` | View name spoofing logs |
| `/ac-command [enable\|disable] [cmd]` | Enable or disable a command |
| `/ac-prefix [prefix]` | Change the chat prefix |

### Detection Toggles

| Command | Description |
|---------|-------------|
| `/ac-fly` | Toggle fly/hover detection |
| `/ac-killaura` | Toggle kill aura detection |
| `/ac-reach` | Toggle reach hack detection |
| `/ac-autoclicker [maxcps]` | Toggle autoclicker detection (optionally set max CPS) |
| `/ac-scaffold` | Toggle scaffold detection |
| `/ac-xray` | Toggle X-ray detection |
| `/ac-gamemode` | Toggle gamemode change detection |
| `/ac-afk [timeout]` | Toggle AFK detection (optionally set timeout) |
| `/ac-vision` | Toggle aimbot/snap detection |
| `/ac-worldborder [radius] [x] [z]` | Set world border radius and center |
| `/ac-lagclear [interval]` | Toggle lag clear (optionally set interval) |
| `/ac-ratelimit` | Toggle packet rate limiting |
| `/ac-namespoof` | Toggle name spoofing detection |
| `/ac-packetmonitor` | Toggle packet spam monitoring |

### Utility

| Command | Description |
|---------|-------------|
| `/ac-home [set\|delete\|list\|help] [name]` | Manage home locations (max 5 per player) |
| `/ac-tpr [radius]` | Teleport to a random location |
| `/ac-pvp [global\|status\|help]` | Toggle PvP (personal or global) |
| `/ac-channels [create\|join\|leave\|list\|send]` | Private chat channels |
| `/ac-invsee <player>` | View a player's inventory |
| `/ac-rank <player> [rank]` | Set or view a player's display rank |
| `/ac-debug-db [table] [key]` | Inspect the database directly |
| `/ac-gui` | Open the full admin GUI |
| `/ac-about` | View plugin version and info |

---

## 🖥️ GUI System

Type `/ac-gui` to open the complete admin panel. **Every feature is accessible from here** — you never need to memorize a command.

### Main Menu

```
┌──────────────────────────────────┐
│     🛡️ Paradox AntiCheat         │
│──────────────────────────────────│
│  ✅ Modules        │  ⚔️ Moderation │
│  👥 Players        │  🔧 Utilities   │
│  🔒 Security       │  ⚙️ Settings    │
│  📋 Commands       │  💾 Database    │
└──────────────────────────────────┘
```

| Section | What You Can Do |
|---------|-----------------|
| **Modules** | Toggle all 14 detection modules on/off with a single tap |
| **Moderation** | Vanish, lockdown, kick, ban, unban, freeze, punish, despawn entities, manage allow/white lists, view spoof logs, change prefix |
| **Players** | Select any online player → kick, ban, freeze, warn, teleport to/from them, set rank, view inventory — all from one screen |
| **Utilities** | Homes (set, delete, update, teleport), random TP, PvP toggle (personal + global), chat channels (create, join, leave, send), TPA, ranks |
| **Security** | Live dashboard: lockdown status, frozen/vanished/banned counts, per-player clearance levels, opsec report |
| **Settings** | Lockdown toggle, AFK timeout, lagclear interval, max CPS, world border radius, global PvP — all in one form |
| **Commands** | Enable/disable any of the 31 commands — see status at a glance |
| **Database** | Browse all database tables, inspect entries |

---

## ⚙️ Configuration

Settings are managed through commands, the GUI, or directly via the database.

### Key Settings

| Setting | Default | How to Change |
|---------|---------|---------------|
| AFK Timeout | 600 sec | `/ac-afk 300` or GUI → Settings |
| Lag Clear Interval | 300 sec | `/ac-lagclear 120` or GUI → Settings |
| Max CPS | 20 | `/ac-autoclicker 25` or GUI → Settings |
| World Border Radius | 10000 | `/ac-worldborder 5000` or GUI → Settings |
| Global PvP | Enabled | `/ac-pvp global` or GUI → Settings |

### Database Location

```
plugins/ParadoxAC/paradox.db
```

All data is stored in SQLite with WAL mode. Use `/ac-debug-db` or the GUI's Database section to inspect tables directly.

---

## 🏗️ Architecture

```
endstone-paradox/
├── pyproject.toml              # Build configuration
├── README.md
└── src/endstone_paradox/
    ├── __init__.py
    ├── paradox.py              # Main plugin (31 commands, event handlers)
    ├── database.py             # SQLite persistence (WAL mode)
    ├── security.py             # 4-level clearance + SHA-256 auth
    ├── modules/                # 16 detection modules
    │   ├── base.py             #   Abstract base class
    │   ├── fly.py              #   Flight/hover detection
    │   ├── killaura.py         #   Combat bot detection
    │   ├── reach.py            #   Reach hack detection
    │   ├── autoclicker.py      #   CPS tracking
    │   ├── scaffold.py         #   Speed bridge detection
    │   ├── xray.py             #   X-ray mining detection
    │   ├── gamemode.py         #   Gamemode change blocking
    │   ├── namespoof.py        #   Name validation
    │   ├── self_infliction.py  #   Self-damage detection
    │   ├── afk.py              #   AFK idle tracking
    │   ├── vision.py           #   Aimbot detection
    │   ├── world_border.py     #   Border enforcement
    │   ├── lag_clear.py        #   Entity cleanup
    │   ├── rate_limit.py       #   Packet flood detection
    │   ├── packet_monitor.py   #   Packet spam alerts
    │   └── pvp_manager.py      #   PvP toggle system
    ├── commands/
    │   ├── moderation/         # 18 admin/moderation commands
    │   ├── settings/           # Module toggle handler
    │   └── utility/            # 9 utility commands
    └── gui/
        └── form_generator.py   # Full GUI (8 sections, 700+ lines)
```

---

## ❓ FAQ

<details>
<summary><strong>How do I set up admin access for the first time?</strong></summary>

Join the server and type `/ac-op YourPassword`. The first password you use becomes the permanent admin password. You'll get Level 4 clearance (full access). To give other players admin, share the password — they can use `/ac-op` with it too.
</details>

<details>
<summary><strong>Can I use the GUI for everything?</strong></summary>

Yes! Type `/ac-gui` and you have full access to every feature. You can toggle modules, kick/ban/freeze players, manage homes, toggle PvP, manage channels, change settings, enable/disable commands, and browse the database — all without typing a single command.
</details>

<details>
<summary><strong>How do I disable a specific detection module?</strong></summary>

Either use the command (e.g., `/ac-fly` to toggle fly detection) or open `/ac-gui` → **Modules** and tap the module to toggle it.
</details>

<details>
<summary><strong>How do I reset my admin password?</strong></summary>

Delete the `security` table entry in the database. You can use `/ac-debug-db security password` to inspect it, then restart the server and run `/ac-op NewPassword` to set a fresh password.
</details>

<details>
<summary><strong>How do homes work?</strong></summary>

Each player can save up to 5 homes. Use `/ac-home set MyBase` to save your location, `/ac-home MyBase` to teleport back, `/ac-home list` to see all homes, and `/ac-home delete MyBase` to remove one. Or use `/ac-gui` → **Utilities** → **Homes** for a visual interface.
</details>

<details>
<summary><strong>What happens during a lockdown?</strong></summary>

When lockdown is active (`/ac-lockdown` or via GUI), only Level 4 admins can use commands. All other players are restricted until lockdown is disabled.
</details>

---

## 📄 License

GPL-3.0 — see [LICENSE](LICENSE) for details. Originally licensed under GPL-3.0 by [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat).

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/TheNINJALLO">TheNINJALLO</a> — based on <a href="https://github.com/Visual1mpact/Paradox_AntiCheat">Paradox AntiCheat</a> by Visual1mpact</sub>
</p>
