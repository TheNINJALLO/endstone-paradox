# Module controls

List module states with `/ac-modules` or `/ac-modstate`. Listing requires clearance 3 or `paradox.modules`. Changing through these commands additionally requires clearance 4 or `paradox.settings`.

```text
/ac-modstate fly on
/ac-modstate timer off
/ac-modules
```

The generic syntax is `/ac-modstate <module> on|off` (also accepted by `/ac-modules`). State persists to SQLite and takes precedence over TOML defaults. Most `/ac-<module> on|off` shortcuts require clearance 4 or `paradox.settings`; use the generic form consistently because some names also serve utilities.

| Special command | Meaning |
| --- | --- |
| `/ac-pvp ...` | Player/global PvP policy; use `/ac-modstate pvp on\|off` for its server module |
| `/ac-chunkborders` | Personal particle display; use the generic command for its server module |
| `/ac-landclaim ...` | Claim operations; use the generic command for its server module |
| `/ac-evidencereplay on\|off` | Toggle recording; a player argument instead reviews the latest replay |
| `/ac-afk <seconds>` | Set and persist inactivity timeout, 60-86400 seconds, and enable AFK |
| `/ac-lagclear <seconds>` | Set and persist scheduled-cleanup interval, 60-86400 seconds, and enable the module; removal configuration still applies |
| `/ac-worldborder <radius> [x] [z]` | Set circular border and center; radius 0 disables the boundary |
| `/ac-lockdown on\|off [kick]` | Explicit access policy; requires clearance 4 or `paradox.lockdown` |

The generic commands accept `all`, which affects utility and restrictive policy modules as well as detectors. Configure individual modules after reading their behavior instead of treating all modules as interchangeable checks.

The old Python sensitivity command is not supported. Native heuristics remain observational regardless of old sensitivity values. See [all 54 defaults](../modules/overview.md), [configuration precedence](../configuration.md) and [enforcement modes](../violation-engine.md).
