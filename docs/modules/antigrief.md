# Anti-Grief / World Protection

> Anti-nuke, rapid placement detection, and explosion audit logging.

## Overview

The Anti-Grief module protects the world from mass destruction tactics. It monitors block break and placement rates per player and maintains an explosion audit log.

## Features

| Feature | Description |
|---------|-------------|
| **Anti-Nuke** | Flags players who break too many blocks in a short window (configurable threshold) |
| **Rapid Placement** | Flags high-speed block placement (grief-style rapid builds) |
| **Explosion Logging** | Tracks TNT, creeper, and other explosions with coordinates, timestamps, and source type |
| **Sensitivity Scaling** | Thresholds scale with module sensitivity (1-10) |
| **Auto-Cancel** | Cancels block break/place events when flagged |

## Configuration

```
/ac-debug-db config antigrief_break_limit 45       # Max breaks per window
/ac-debug-db config antigrief_break_window 3.0     # Window in seconds
/ac-debug-db config antigrief_place_limit 40       # Max placements per window
/ac-debug-db config antigrief_place_window 3.0     # Window in seconds
/ac-debug-db config antigrief_log_explosions true   # Enable explosion audit trail
```

## Explosion Log

The last 500 explosions are stored in the database with:
- Source type (TNT, creeper, etc.)
- X, Y, Z coordinates
- Dimension
- Timestamp

View via `/ac-debug-db logs explosions`.

## Default State

**ON** — Active by default with generous thresholds.
