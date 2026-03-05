# Anti-Knockback Detection

> Detects players who don't take knockback after being hit.

## How It Works

Tracks player displacement after receiving damage. If a player doesn't move at least 0.1 blocks within 3 ticks of being hit, the module flags it. Requires **3 flags** before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Minimum displacement | 0.1 blocks |
| Check window | 3 ticks after hit |
| Flags required | 3 |
| Level 4 exempt | Yes |

## Default State

**ON**
