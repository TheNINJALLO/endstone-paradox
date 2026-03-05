# Wall Hit / Line of Sight Detection

> Detects players hitting through solid blocks.

## How It Works

When damage occurs, the module raycasts from the attacker's eye position to the victim's position. If any solid block lies along the line of sight, the hit is flagged as hitting through walls. Requires **3 flags** before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Ray origin | Attacker eye position |
| Ray target | Victim position |
| Flags required | 3 |
| Level 4 exempt | Yes |

## Default State

**ON**
