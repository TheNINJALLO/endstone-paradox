# Packet Monitor

## Overview
Diagnostic tool that monitors packet frequency by type per player.

## How It Works
1. **Per-Type Tracking**: Counts each packet type separately per player
2. **Spam Detection**: Flags players sending excessive amounts of a specific packet type
3. **Noise Filtering**: Common high-frequency packets (MovePlayer, PlayerAuthInput, LevelChunk) are ignored

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Spam Threshold | 1000 | Packets per type per 5 seconds |
| Command | `/ac-packetmonitor` | Toggle on/off |

> **Note**: This is a diagnostic tool, OFF by default. Useful for identifying unfamiliar exploit packets.