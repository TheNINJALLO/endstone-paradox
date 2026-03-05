# NoClip / Phase Detection

> Detects players walking through solid blocks.

## How It Works

The NoClip module ray-traces the player's movement path between ticks. It samples 3 points along the path and checks whether they pass through solid blocks. If the trace hits solid geometry, the module increments a flag counter. After **3 consecutive flags**, the module emits a violation to the violation engine.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Samples per check | 3 (along movement vector) |
| Flags required | 3 consecutive |
| Level 4 exempt | Yes |

## Default State

**ON**
