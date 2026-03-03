# World Border

## Overview
Enforces a configurable world border with automatic teleport-back.

## How It Works
1. **Radius Check**: Monitors player positions against a configurable center + radius
2. **Teleport-Back**: Players who cross the border are teleported to the nearest valid position
3. **Per-Dimension**: Can be configured independently for each dimension

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | N/A | Border radius is set separately |
| Command | `/ac-worldborder` | Toggle on/off |

Set border via the GUI or config file.