# Getting Started

## Requirements

- **Endstone** server for Minecraft Bedrock Edition
- **Python 3.9+** on the server machine
- The `endstone-paradox` wheel file (`.whl`)

## Installation

### Step 1: Download the Plugin

Download the latest `.whl` file from the [Releases page](https://github.com/TheNINJALLO/endstone-paradox/releases).

### Step 2: Install the Plugin

Place the `.whl` file in your Endstone server's `plugins/` directory:

```
your-server/
├── plugins/
│   └── endstone_paradox-1.5.0-py3-none-any.whl
├── endstone.toml
└── ...
```

### Step 3: Start Your Server

Start (or restart) your Endstone server. You should see Paradox load in the console:

```
[Paradox] ════════════════════════════════════════════════════════
[Paradox]   AntiCheat v1.5.0
[Paradox]   Designed by Visual1mpact
[Paradox]   Ported to Endstone by TheN1NJ4LL0
[Paradox] ════════════════════════════════════════════════════════
[Paradox] Module 'fly' started
[Paradox] Module 'killaura' started
...
[Paradox] Loaded successfully!
[Paradox] Modules loaded: 20
```

### Step 4: Set Up Your Admin Password

Join your server and run:

```
/ac-op
```

A GUI form will appear asking you to set a new admin password. This uses **SHA-256 hashing** — your password is never stored in plaintext.

Once authenticated, you'll be set to **Clearance Level 4** (full admin). See [Security & Clearance](security.md) for details on the clearance system.

### Step 5: Configure Modules

By default, most detection modules are **enabled**. A few advanced modules are **disabled by default** and need per-server tuning:

| Module | Default | Why |
|--------|---------|-----|
| Rate Limiter | OFF | Needs threshold tuning per server |
| Packet Monitor | OFF | Diagnostic tool for admins |
| Container See | OFF | Admin-only vision tool |
| Anti-Dupe | OFF | Needs testing per server |
| Crash-Drop | OFF | Needs radius/timing tuning |
| Inventory Sync | OFF | Needs tolerance tuning |

Toggle modules via:
- **In-game**: `/ac-modules <name> <on/off>`
- **GUI**: `/ac-gui` → Module Management
- **Web UI**: Navigate to the Modules page

### Step 6: (Optional) Enable the Web Admin Panel

The web UI starts automatically on port `8005`. Access it at:

```
http://your-server-ip:8005
```

The default secret key is configured in `config.toml`. See [Web Admin Panel](webui.md) for full setup instructions.

## Next Steps

- Browse the [Modules](modules/overview.md) documentation to understand each detection system
- Review all [Commands](commands/moderation.md)
- Set up the [Web Admin Panel](webui.md) for remote management
