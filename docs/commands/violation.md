# Evidence and enforcement commands

| Command | Behavior | Authorization |
| --- | --- | --- |
| `/ac-case <player>`, `/ac-history <player>` | Up to 100 persisted findings; resolves online players or stored name history | Clearance 3 or `paradox.case` |
| `/ac-evidencereplay <player>` | Latest bounded replay if recorded; not all historical replays | Clearance 3 or `paradox.case` |
| `/ac-watch <player> [seconds]` | Receive target alerts for 1-3600 seconds; default 300; target online and sender in game | Clearance 3 or `paradox.watch` |
| `/ac-exempt <player> <module\|all> [seconds]` | Temporary detection exemption for 1-3600 seconds; default 300; target online | Clearance 3 or `paradox.exempt` |
| `/ac-mode [soft\|hard\|logonly]` | Inspect/change mode; changing resets detection history | Clearance 4 or `paradox.settings` |

Intervals are in **seconds**. The historical `/ac-watch stop` and optional case-count syntax are not native command forms. Watches expire automatically. For permanent identity exemptions, authorized staff can use the [allowlist](moderation.md).

Use `/ac-evidencereplay on|off` to configure recording with clearance 4 or `paradox.settings`. Findings store their action, reason, value/limit, ping and health context; observed behavior is not a confirmed cheat. See [enforcement and lag recovery](../violation-engine.md) before acting on it.
