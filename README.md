# Paradox Native 2.0.0 (preview)

C++23 anti-cheat monitoring, moderation and administration for **Endstone 0.11.11 / BDS 1.26.51.1 (protocol 2193)**, on Windows and Linux x86-64. Based on [Visual1mpact's Paradox](https://github.com/Visual1mpact/Paradox_AntiCheat), reviewed through v6.9.1.

The plugin runs as a native `.dll` or `.so`. Endstone itself still uses its normal runtime and bootstrap. The Python implementation is archived under [`legacy/python`](legacy/python); do not load both implementations.

## Install or migrate

1. Stop the server and back up `plugins/paradox` and your world.
2. Remove the old Paradox wheel from `plugins`, or uninstall `endstone-paradox` from the Python environment used by Endstone if installed there.
3. Copy **one** native binary into `plugins/`: `endstone_paradox.dll` on Windows, or `endstone_paradox.so` on Linux. Linux requires OpenSSL 3 (`libssl3` / `libssl3t64`).
4. Keep the existing `plugins/paradox/config.toml` and `paradox.db`. The loader creates `paradox.db.pre-native.bak` using SQLite's consistent backup API. Existing tables remain intact.
5. Start Endstone and check for `Paradox 2.0.0 native enabled; 54 modules`. The server must report supported protocol 2193. `ac-about` and `ac-debug-db` work from the console.
6. Grant staff clearance from the console: `ac-setclearance "Player Name" 4`. Review the [migration notes](native/MIGRATION.md) before enabling server policies.

The supplied BDS ZIPs are verification inputs and are **not redistributed**. [`verify-server.py`](native/tools/verify-server.py) checks both archive and executable against pinned official metadata.

## Lag and false positives

Movement detection pauses during high/unknown ping, jitter, slow server ticks, packet bursts or gaps, unloaded terrain, joins, teleports, respawns, dimension changes, knockback, effects and special movement. It clears previous samples and requires a recovery interval with stable updates.

Unchanged yaw and straight-line movement never produce a robotic-pathing violation. Physics, aim, clicking, mining and inventory heuristics produce review observations; repeating them never turns them into kicks or bans. Timer and repeated excessive melee reach require healthy evidence. Malformed inspected inputs may be cancelled, but never automatically ban a player. There are **no automatic bans**.

`soft` is the default enforcement mode; `logonly` records findings without acting; `hard` permits kicks after repeated corroborated evidence. Explicit staff bans, whitelist/lockdown restrictions, AFK configuration and land/container policies are separate administrative actions.

Automated regressions and real BDS startup tests do not establish that every client, custom item, physics interaction or network condition is free of false positives. Live multi-client gameplay, latency and packet-loss testing remains necessary before relying on hard enforcement. See the [module audit](native/MODULE_AUDIT.md) and [validation record](native/VALIDATION.md).

## Common commands

Quote player names containing spaces.

| Command | Purpose |
| --- | --- |
| `/ac-gui`, `/ac-guiitem` | In-game controls and menu compass |
| `/ac-modules`, `/ac-modstate <module> on\|off` | Review/configure the 54 modules |
| `/ac-mode soft\|hard\|logonly` | Set enforcement mode |
| `/ac-case <player>`, `/ac-history <player>` | Review saved findings |
| `/ac-evidencereplay <player>` | Review the latest bounded position replay |
| `/ac-watch <player> [seconds]` | Receive a player's review alerts |
| `/ac-exempt <player> <module\|all> [seconds]` | Temporarily suspend checks |
| `/ac-setclearance <player> <1..4>` | Assign staff clearance |
| `/ac-ban`, `/ac-unban`, `/ac-kick`, `/ac-freeze`, `/ac-punish` | Manual moderation |
| `/ac-allowlist add\|remove\|list <player>` | Detection exemptions using identity history |
| `/ac-whitelist add\|remove\|list\|on\|off` | Access policy, including previously joined offline players |
| `/ac-lockdown on\|off [kick]` | Lock new joins; retain online players unless `kick` is explicit |
| `/ac-home set\|delete\|list\|tp [name]`, `/ac-waypoint ...` | Locations with fractional coordinates and dimension |
| `/ac-tpa <player>`, `/ac-tpa accept\|deny`, `/ac-tpr [radius]` | Teleport requests and safe random loaded destinations |
| `/ac-pvp [on\|off\|status\|global]` | Personal/server PvP policy and combat cooldowns |
| `/ac-landclaim create\|delete\|list\|trust\|untrust [name] [value]` | Land policy; enable before creating claims |
| `/ac-chunkborders`, `/ac-worldborder <radius> [x] [z]` | Chunk display and circular world border |
| `/ac-invsee <player>`, `/ac-inventory-editor <player> <slot> clear\|<item> [amount]` | Inventory administration |
| `/ac-invclone <player>`, `/ac-vanish`, `/ac-rank <player> <rank>` | Staff utilities |
| `/ac-ping`, `/ac-tps`, `/ac-debug-db`, `/ac-about` | Diagnostics |

Moderation requires clearance 3 or the corresponding checked `paradox.*` permission. Security/settings changes require clearance 4 or the checked staff permission. Endstone operators receive staff permissions by default. Ordinary utility permissions default to true; `paradox.bypass` defaults to false. Native handlers check authorization again for GUI and web command routing.

## Web interface and integrations

New installs bind to `127.0.0.1:8080`. Read the access token from `plugins/paradox/web-token.txt` and use it to connect. The token grants administration access. Existing configured host/port settings are preserved. For remote access, terminate HTTPS at a reverse proxy or use an SSH tunnel.

The dashboard shows online connection health, module switches and recent evidence, and queues Paradox commands onto the server thread. SQLite writes and HTTPS integrations run on bounded workers. Global integration is disabled on new installs; explicitly configure an HTTPS `api_url` and optional `api_key`. Name-only remote records remain review evidence and do not ban players. Discord uses the configured HTTPS webhook. See [configuration and migration](native/MIGRATION.md).

## Build and provenance

See [native/BUILDING.md](native/BUILDING.md). CMake pins dependencies; the decoder applies allocation/depth inspection budgets. [`references.lock.json`](native/references.lock.json) records all seven requested Endstone repositories, upstream Paradox and both server checksums.

Endstone's native plugin API supplies the server hooks and ABI boundary. This port does not guess private BDS offsets or install a second set of detours. The supplied Linux binary is stripped, so `dwarf2cpp` cannot generate complete private class headers from it. This constraint and the protocol-dumper evidence are documented in [VALIDATION.md](native/VALIDATION.md).

GPL-3.0-or-later. Original Paradox by Visual1mpact; Endstone port by TheNINJALLO. Third-party notices are in [`native/licenses`](native/licenses).
