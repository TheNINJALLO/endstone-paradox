# AFK Detection

## Overview
Tracks idle players and kicks them after configurable inactivity.

## How It Works
1. **Position Tracking**: Monitors each player's position at regular intervals
2. **Warning System**: Sends chat warnings before kicking (30s, 15s, 5s countdown)
3. **Activity Reset**: Any movement resets the AFK timer

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = shorter AFK timeout |
| Command | `/ac-afk` | Toggle on/off |