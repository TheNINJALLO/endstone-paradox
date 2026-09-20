# Paradox Native 2.0.1

Paradox is a C++23 plugin for anti-cheat monitoring, moderation and server administration. The supported release targets **Endstone 0.11.11**, **BDS 1.26.51.1 / protocol 2193**, and **Windows or Linux x86-64**. It adapts [Visual1mpact's Paradox](https://github.com/Visual1mpact/Paradox_AntiCheat), reviewed through v6.9.1.

[Download stable v2.0.1](https://github.com/TheNINJALLO/endstone-paradox/releases/tag/v2.0.1) and follow [installation](gettingstarted.md) or [migration](migration.md). The older v2.0.0 preview has a command authorization defect and is superseded; upgrade it.

## What the native release provides

- **54 modules** covering monitoring, input validation, server policies and utilities. [Every module's behavior and default](modules/overview.md) is documented.
- Connection health gates that suspend detection during lag, packet recovery, unloaded terrain and gameplay transitions. Straight movement and constant yaw are normal.
- SQLite persistence, consistent migration backups, fractional home coordinates and staff clearance.
- Native in-game forms and a bearer-token dashboard. Administrative actions check authorization in the native handlers.
- Windows/Linux native regressions and real BDS integration and scripted multiplayer acceptance checks. See the [validation record](validation.md).

Heuristic findings are review observations and never accumulate into automatic punishment. Corroborated timer/reach evidence and malformed inspected inputs follow the [enforcement rules](violation-engine.md). Detection never creates automatic bans. Explicit staff bans and server access policies are separate.

## Find the right guide

| Task | Guide |
| --- | --- |
| Install or upgrade | [Getting started](gettingstarted.md), [migration and API limits](migration.md) |
| Configure modules and server policies | [Configuration](configuration.md), [module overview](modules/overview.md) |
| Assign staff and review evidence | [Security](security.md), [moderation commands](commands/moderation.md), [evidence commands](commands/violation.md) |
| Use homes, teleports, claims and PvP | [Utility commands](commands/utility.md) |
| Connect the dashboard | [Web interface](webui.md) |
| Understand lag protection and testing | [Enforcement](violation-engine.md), [validation](validation.md), [module audit](module-audit.md) |
| Build or contribute | [Build instructions](building.md), [architecture](architecture.md), [documentation maintenance](maintenance.md) |

The Python 1.9.4 implementation is [archived for reference](https://github.com/TheNINJALLO/endstone-paradox/tree/main/legacy/python). Do not load it alongside the native binary. Endstone still uses its normal runtime/bootstrap; converting this plugin does not remove Endstone's own requirements.

GPL-3.0-or-later. Original Paradox by Visual1mpact; Endstone port by TheNINJALLO. [Third-party notices](https://github.com/TheNINJALLO/endstone-paradox/blob/main/native/licenses/README.md).
