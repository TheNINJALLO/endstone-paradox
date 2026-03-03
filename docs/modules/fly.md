# Fly Detection

## Overview
Detects flight and hover hacks by analyzing player movement patterns.

## How It Works
1. **Surrounding Block Check**: Examines blocks around the player in a multi-block radius. If the majority of surrounding blocks are air (the player is not near any solid surface), they are flagged.
2. **Velocity Analysis**: Monitors vertical velocity — legitimate players fall or jump with predictable acceleration.
3. **Exemptions**: Players using tridents (Riptide enchantment), elytra, or in creative mode are automatically exempted.

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | 1-10 scale. Higher = stricter air-block majority threshold |
| Command | `/ac-fly` | Toggle on/off |

## Actions
- **Alert**: Notifies L4 admins with player name and coordinates
- **Escalation**: At repeated violations, the player may be teleported to ground level