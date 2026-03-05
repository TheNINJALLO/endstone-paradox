# Blink / Teleport Detection

> Detects instant position jumps without server teleport events.

## How It Works

Monitors player position between ticks. If a player moves more than 10 blocks in a single tick without a corresponding server teleport event, the module flags it. Includes a 3-second grace period after legitimate teleports. Requires **2 flags** before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Distance threshold | >10 blocks per tick |
| Grace period | 3 seconds after server teleport |
| Flags required | 2 |
| Level 4 exempt | Yes |

## Default State

**ON**
