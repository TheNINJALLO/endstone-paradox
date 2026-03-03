# Violation Engine Commands

These commands control the centralized violation processing engine.

## Commands

| Command | Description | Min. Clearance |
|---------|-------------|----------------|
| `/ac-case <player> [count]` | View last N violation entries for a player (default: 5) | L3 |
| `/ac-watch <player> [minutes]` | Stream a player's violations to your chat in real-time | L3 |
| `/ac-watch stop` | Stop watching | L3 |
| `/ac-mode <logonly\|soft\|hard>` | Set enforcement mode | L4 |
| `/ac-mode` | View current enforcement mode | L4 |
| `/ac-exempt <player> <module\|all> [min]` | Temporarily exempt a player from detection (default: 10 min) | L4 |

## Examples

### View a suspicious player's evidence

```
/ac-case PlayerName
/ac-case PlayerName 20
```

Shows timestamps, module names, severity, evidence details, and what action was taken.

### Watch a player in real-time

```
/ac-watch PlayerName 10
```

Streams all violations for PlayerName to your chat for the next 10 minutes. You'll see every flag as it happens.

### Switch to monitoring-only mode

```
/ac-mode logonly
```

All detection continues but no enforcement actions are taken — useful during server events or when testing.

### Exempt a player from fly detection

```
/ac-exempt PlayerName fly 30
```

Exempts PlayerName from fly detection for 30 minutes. Use `all` instead of a module name to exempt from everything.

## Enforcement Modes

See [Violation Engine](violation-engine.md) for full details on modes and the enforcement ladder.
