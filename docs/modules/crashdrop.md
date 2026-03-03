# Crash-Drop Module

## Overview
Prevents crash/disconnect duplication exploits by tracking player locations and removing suspicious item entities near disconnect points.

## How It Works

### Location Tracking
Every few ticks, the module records each player's current position and dimension. This provides a reliable "last known location" when the player disconnects.

### Disconnect Item Removal
When a player disconnects (crash, kick, or leave):
1. Their last known position is recorded with a timestamp
2. Any item entities that spawn near that position within the configurable time window are flagged as suspected dupe items
3. Flagged items are logged and can be automatically removed

### Rapid Disconnect Detection
Monitors disconnect frequency per player. If a player disconnects 3+ times in 60 seconds, it's flagged as a **crash-dupe pattern** — admins are alerted.

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Default State | OFF | Needs radius/timing tuning |
| Sensitivity | 5 | Higher = wider removal radius, longer time window |
| Removal Radius | 3 blocks (at sens 5) | Area around disconnect point |
| Time Window | 3 seconds (at sens 5) | How long after disconnect to monitor |
| Command | `/ac-modules crashdrop` | Toggle on/off |