# Enforcement, lag and false positives

Native detection separates observations from corroborated evidence and invalid inspected inputs. **No detection module automatically bans players.** A repeated review observation stays an observation, including in hard mode.

## Enforcement modes

| Mode | Behavior |
| --- | --- |
| `logonly` | Records findings without detection enforcement |
| `soft` | Default; permits validated input cancellation and conservative responses to repeated corroborated evidence |
| `hard` | Adds kicks after repeated corroborated evidence; never turns observational heuristics into punishment |

Use `/ac-mode logonly` for initial acceptance testing on your own server. A mode change resets detection history. Existing stored modes survive migration. Explicit staff moderation and configured server policies still apply independently of this mode.

Movement/aim/clicking/mining/inventory heuristics are for review. Straight movement and unchanged yaw never cause a robotic-pathing violation. [Timer](modules/timer.md) and [reach](modules/reach.md) need repeated, healthy evidence; slow input and a lagging target do not prove cheating. Malformed inspected packets or impossible selected hotbar slots can be cancelled without a ban.

## Connection health and recovery

Checks pause during high, unknown or non-finite ping; jitter; slow server ticks; scheduling gaps; packet gaps, bursts or reordered input; unloaded terrain; and join, respawn, teleport or dimension transitions. Effects, knockback and special movement also reset relevant evidence. Recovery requires stable updates before detection resumes.

The timer guard retains a session clock anchor across resets. A delayed backlog must catch up before it can be treated as client-clock acceleration. This deliberately trades detection coverage for avoiding punishment during recovery. A zero-millisecond rounded ping is treated as unknown, so a localhost session alone cannot prove active detection.

Check `/ac-ping [player]` or the dashboard for readiness and its suspension reason, and `/ac-tps` for server health. Do not interpret a suspended detector as an accusation or a client disconnect timeout.

## Reviewing a report

1. Inspect `/ac-case <player>` or `/ac-history <player>` for the action, evidence, ping and health.
2. Review `/ac-evidencereplay <player>` when recording is enabled. It contains the latest bounded replay, not a complete session recording.
3. Check server load, network recovery, custom movement/items and other plugins before deciding on moderation.
4. Use `/ac-watch <player> [seconds]` or `/ac-exempt <player> <module|all> [seconds]` while investigating. Both intervals default to 300 seconds and accept 1 through 3600 seconds.

History is bounded to 100 entries per player; the recent dashboard list holds 50 entries. Observational findings must not be presented as confirmed cheating or a guaranteed reason to ban.

The release passed native regressions and scripted connected-client lag/gameplay acceptance on both platforms. Retail controller/touch clients, unusual physics and custom plugin combinations still require local testing. See [exact validation scope](validation.md) and [the full module audit](module-audit.md).
