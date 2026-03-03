<p align="center">
  <img src="Icon.png" alt="Paradox AntiCheat" width="200">
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
    <a href="https://theninjallo.github.io/endstone-paradox/">
      <img src="https://img.shields.io/badge/Docs-Documentation-22c55e?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Documentation">
    </a>
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
│   └── endstone_paradox-1.5.2-py3-none-any.whl   ← drop it here
└── ...
```

### Step 3 — Start the Server

Start (or restart) your Endstone server. You'll see Paradox load in the console:

```
[ParadoxAC] Paradox AntiCheat v1.5.2 loaded!
[ParadoxAC] Database initialized at plugins/ParadoxAC/paradox.db
[ParadoxAC] 20 detection modules registered.
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

### 🛡️ 20 Detection & Admin Modules

| Module | What It Detects |
|--------|-----------------|
| **Fly** | Flight/hover hacks — surrounding-block air-majority check, velocity analysis, trident exemption |
| **KillAura** | Combat bots — dynamic threshold adaptation, facing angle validation, attack rate + pattern analysis |
| **Reach** | Extended reach hacks — Catmull-Rom cubic interpolation for accurate distance checks |
| **AutoClicker** | Click bots — per-platform CPS (PC/Mobile/Console), air-click tracking via packets, click consistency (CV) analysis |
| **Scaffold** | Speed bridging — air-below filtering, axis pattern analysis, excludes sneaking/farmland |
| **X-Ray** | Mining hacks — weighted suspicion scoring, hidden ore detection, vein-jumping, ore ratios, suspicion decay, graduated escalation (alert → priority → freeze) |
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
| **Container See** | Admin tool — see container contents and player inventories by looking at them (L4 only, off by default) |
| **Anti-Dupe** | 4-layer duplication prevention — bundle blocking, hopper cluster monitoring (allows clocks), piston entity tracking, packet analysis (off by default) |
| **Crash-Drop** | Anti-crash-drop — tracks disconnect locations, removes duped item entities, detects rapid disconnect cycling (off by default) |
| **Inv-Sync** | Inventory synchronization — DB-persisted snapshots, detects excess items on rejoin from dupe exploits (off by default) |

Every module can be toggled individually via commands **or** the GUI. The 3 anti-dupe modules are **off by default** and should be tuned per-server.

#### 🎚️ Module Sensitivity

All detection modules support a **sensitivity scale from 1 to 10**:

| Sensitivity | Behavior |
|:-----------:|----------|
| **1** | Very lenient — fewer false positives, may miss subtle cheats |
| **5** | Default — balanced detection |
| **10** | Very strict — catches more, but may flag edge cases |

Adjust per module via command (`/ac-fly sensitivity 8`) or the GUI → **Modules** → select a module → **Adjust Sensitivity**.

### 🔐 4-Level Security System

| Level | Name | Access |
|-------|------|--------|
| 1 | Standard | Utility commands (home, tpr, pvp, channels) |
| 2 | Moderator | Player management (kick, freeze, warn) |
| 3 | Admin | Settings and module control |
| 4 | Owner | Full access — all commands, exempt from detection |

- **SHA-256 password hashing** — your password is never stored in plain text
- **Security broadcasts** — all admin actions are reported to Level 4 players
- **Two-tier lockdown mode:**
  - **Level 1** — Only Level 4 (Owner) can stay and use commands
  - **Level 2** — Level 4 + Level 3 (Moderator) can stay and use commands

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
| `/ac-lockdown` | Toggle server lockdown |
| `/ac-lockdown level 1` | Set lockdown to Level 4 only |
| `/ac-lockdown level 2` | Set lockdown to Level 4 + Level 3 |
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
| `/ac-fly sensitivity 7` | Set fly detection sensitivity (1-10) |
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
| `/ac-containersee` | Toggle container vision for admins (off by default) |

> **Tip:** Any detection command accepts `sensitivity N` — e.g., `/ac-killaura sensitivity 3` for lenient or `/ac-xray sensitivity 9` for strict.

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
| **Modules** | Toggle all 17 detection modules on/off, adjust sensitivity per-module with a slider (1-10) |
| **Moderation** | Vanish, lockdown, lockdown level selector (L4 only / L4+L3), kick, ban, unban, freeze, punish, despawn entities, manage allow/white lists, view spoof logs, change prefix |
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
| Module Sensitivity | 5 (per module) | `/ac-fly sensitivity 8` or GUI → Modules → module → Sensitivity |
| Lockdown Level | 1 (L4 only) | `/ac-lockdown level 2` or GUI → Moderation → Lockdown Level |

### Database Location

```
plugins/ParadoxAC/paradox.db
```

### Config File

A `config.toml` is auto-generated in the data folder on first run:

```toml
[web_ui]
enabled = true
port = 8080
host = "0.0.0.0"
secret_key = "<auto-generated>"

[database]
mode = "internal"        # "internal" (SQLite) or "external" (MySQL/PostgreSQL)

[database.external]
type = "mysql"
host = "localhost"
port = 3306
name = "paradox"
user = "paradox"
password = ""

[global_database]          # Cross-server ban list (coming soon)
enabled = false
api_url = ""
api_key = ""
sync_interval = 300
```

---

## 🌐 Web UI Companion

Paradox includes a built-in web admin panel accessible from any browser.

### Setup

1. Start the server — web UI auto-starts on port **8080**
2. Open `http://your-server-ip:8080`
3. Login with the **secret key** from `config.toml`

### Screenshots

| Dashboard | Module Management |
|:---------:|:-----------------:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Modules](docs/screenshots/modules.png) |

| Ban Management |
|:--------------:|
| ![Bans](docs/screenshots/bans.png) |

### Pages

| Page | What You Can Do |
|------|-----------------|
| **Dashboard** | Overview cards: module count, bans (server + 509 global), frozen, vanished, lockdown status, module status table |
| **Modules** | Toggle all 17 modules on/off + adjust sensitivity (1-10 sliders) |
| **Bans** | View server bans, add/remove bans, browse the 509-name Global Ban List with search |
| **Players** | Player records, warnings, frozen/vanished lists, ranks |
| **Permissions** | View and set player clearance levels (1-4) |
| **Logs** | Namespoof detection log, detection events |
| **Config** | Edit all DB settings, view config.toml, database mode info |
| **Allow/Whitelist** | Add/remove players from allowlist and whitelist |
| **Global DB** | Cross-server ban database status (coming soon) |

### Database Modes

| Mode | Backend | Use Case |
|------|---------|----------|
| `internal` | SQLite (default) | Single server, zero setup |
| `external` | MySQL / PostgreSQL | Multi-server or remote panel |

### Global Ban List

Paradox ships with a **hardcoded list of 509 known cheaters** from the [original Paradox AntiCheat](https://github.com/Visual1mpact/Paradox_AntiCheat). Players matching these names are automatically kicked on join. The full list is viewable and searchable in the Web UI's Bans page.

### Global Ban Database (Coming Soon)

A shared cross-server database for **banned members** and **high-risk players**. Configure via `config.toml` → `global_database`.

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
    ├── modules/                # 20 detection & admin modules
    │   ├── base.py             #   Abstract base class + sensitivity
    │   ├── fly.py              #   Flight/hover (surrounding-block check)
    │   ├── killaura.py         #   Combat bot (dynamic thresholds)
    │   ├── reach.py            #   Reach hack (Catmull-Rom interpolation)
    │   ├── autoclicker.py      #   CPS tracking
    │   ├── scaffold.py         #   Speed bridge (air-below filtering)
    │   ├── xray.py             #   X-ray (weighted suspicion scoring)
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
    │   ├── containersee.py     #   Container vision (admin tool)
    │   ├── antidupe.py         #   4-layer dupe prevention (bundles, hoppers, pistons, packets)
    │   ├── crashdrop.py        #   Anti-crash-drop (disconnect item removal)
    │   └── invsync.py          #   Inventory sync (DB snapshots, rejoin diff)
    ├── commands/
    │   ├── moderation/         # 18 admin/moderation commands
    │   ├── settings/           # Module toggle handler
    │   └── utility/            # 9 utility commands
    ├── gui/
    │   └── form_generator.py   # Full GUI (8 sections, 700+ lines)
    ├── config.py               # TOML config loader (DB mode, web UI, global DB)
    ├── globalban.py            # 509 known cheaters from original Paradox
    └── web/                    # Built-in web admin panel
        └── server.py           # Flask server + all routes + embedded templates
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

When lockdown is active (`/ac-lockdown` or via GUI), access is restricted based on the lockdown level:
- **Level 1** (default): Only Level 4 (Owner) can use commands and stay on the server.
- **Level 2**: Level 4 + Level 3 (Moderator) can stay and use commands.

Set the level with `/ac-lockdown level 2` or via GUI → **Moderation** → **Lockdown Level**.
</details>

---

## 📄 License

GPL-3.0 — see [LICENSE](LICENSE) for details. Originally licensed under GPL-3.0 by [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat).

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/TheNINJALLO">TheNINJALLO</a> — based on <a href="https://github.com/Visual1mpact/Paradox_AntiCheat">Paradox AntiCheat</a> by Visual1mpact</sub>
</p>
