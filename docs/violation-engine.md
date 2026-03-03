# Violation Engine

Paradox uses a **centralized violation engine** — all detection modules emit violations to a single processing pipeline instead of punishing players directly.

## How It Works

```
Module detects cheat → emit_violation() → Engine scores severity
                                           ↓
                                    Rolling buffer (5 min decay)
                                           ↓
                                    Cross-module correlation
                                           ↓
                                    Enforcement ladder
                                           ↓
                                    Rate-limited staff alert
                                           ↓
                                    Evidence → SQLite
```

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `logonly` | Log violations and alert staff, but take no action | Testing / monitoring |
| `soft` | Cancel illegal actions, setback when repeated, escalate slowly | **Default — recommended** |
| `hard` | Faster escalation, shorter ladder, quicker bans | High-risk servers |

Set with `/ac-mode <logonly|soft|hard>` (requires Level 4).

## Enforcement Ladder

When violations accumulate, the engine escalates actions automatically:

### Soft Mode
| Score | Action |
|-------|--------|
| 0+ | Warn (alert staff only) |
| 5+ | Cancel (block the illegal action) |
| 15+ | Setback (teleport to last safe position) |
| 40+ | Kick |
| 80+ | Ban |

### Hard Mode
| Score | Action |
|-------|--------|
| 0+ | Cancel |
| 5+ | Setback |
| 15+ | Kick |
| 30+ | Ban |

Scores decay over a **5-minute rolling window** — if a player stops cheating, their score drops back to 0.

## Severity Levels

Each module assigns a severity to its violations:

| Level | Name | Weight | Example |
|-------|------|--------|---------|
| 1 | INFO | 1 | AFK timeout |
| 2 | LOW | 2 | Self-infliction, X-Ray alert |
| 3 | MEDIUM | 3 | KillAura, Fly, Reach, Scaffold |
| 4 | HIGH | 4 | AutoClicker consistency, Gamemode exploit |
| 5 | CRITICAL | 5 | NameSpoof, X-Ray freeze |

## Rate-Limited Alerts

Staff receive at most **1 alert per player per module every 10 seconds** to prevent console/chat spam. Evidence is still logged regardless of alert cooldowns.

## Evidence Persistence

All violations are automatically saved to the `violations` SQLite table with:
- Player UUID and name
- Module name
- Severity level
- Evidence details (distances, CPS, angles, etc.)
- Enforcement action taken
- Timestamp

Evidence is flushed to disk every 30 seconds (write-behind buffering for performance).

View evidence with `/ac-case <player>`.

## Temporary Exemptions

Use `/ac-exempt <player> <module|all> <minutes>` to temporarily disable detection for a player. Useful when:
- Testing new module configurations
- A player reports false positives
- An admin is doing legitimate testing

## Live Watching

Use `/ac-watch <player> [minutes]` to stream all of a player's violations to your chat in real-time. Use `/ac-watch stop` to stop.
