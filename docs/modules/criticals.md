# Criticals Detection

> Detects players who always get critical hits without actually falling.

## How It Works

Monitors attacks where the client reports a critical hit (falling flag set) but the player has minimal Y-axis movement. If ground-level hits consistently claim critical status, the module flags it. Requires **5 flags** before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Flags required | 5 |
| Level 4 exempt | Yes |

## Default State

**ON**
