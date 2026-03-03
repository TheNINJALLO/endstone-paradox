# Introduction

## About Paradox AntiCheat for Endstone

Paradox AntiCheat is a comprehensive anti-cheat plugin for **Minecraft Bedrock Edition** servers running on the **Endstone** framework. Originally created by **Visual1mpact** as a Script API behavior pack, this version has been **fully ported to Python** by **TheN1NJ4LL0** and rebuilt from the ground up to take advantage of Endstone's server-side capabilities.

### Why Endstone?

Unlike the original Script API version, the Endstone port runs **server-side** with full access to:

- **Packet-level interception** — inspect and cancel raw Bedrock protocol packets
- **Direct block/entity manipulation** — no script API limitations
- **SQLite persistence** — data survives pack changes, world copies, and server restarts
- **Python ecosystem** — Flask web servers, advanced algorithms, and more
- **True server authority** — clients can't tamper with detection logic

### Key Features

| Feature | Description |
|---------|-------------|
| **21 Modules** | Detection, prevention, and admin utilities — all individually toggleable |
| **4-Level Security** | Clearance system with SHA-256 authentication (no operator abuse) |
| **Violation Engine** | Centralized enforcement pipeline with rolling buffers, escalation ladder, and evidence logging |
| **Web Admin Panel** | Full-featured web UI with dashboard, module management, bans, players, permissions, anti-dupe monitoring, and more |
| **In-Game GUI** | 8-section form-based GUI accessible via `/ac-gui` |
| **35+ Commands** | 18 moderation + 9 utility + module toggles + violation engine |
| **Sensitivity Scaling** | Every detection module has a 1-10 sensitivity scale |
| **Global Ban List** | 509 known cheaters from the original Paradox, checked on join |
| **Global Ban API** | Separate standalone API for cross-server ban/flag/report sharing |
| **TOML Configuration** | Clean, human-readable config file |

### Credits

- **Original Paradox AntiCheat** — [Visual1mpact](https://github.com/Visual1mpact/Paradox_AntiCheat)
- **Endstone Port** — [TheN1NJ4LL0](https://github.com/TheNINJALLO/endstone-paradox)
- **Endstone Framework** — [Endstone](https://github.com/EndstoneMC/endstone)

For setup instructions, proceed to [Getting Started](gettingstarted.md).
