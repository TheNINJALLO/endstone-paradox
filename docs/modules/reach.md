# Reach Detection

## Overview
Detects extended reach hacks using **Catmull-Rom cubic interpolation** for accurate distance measurement.

## How It Works
1. **Position Interpolation**: Uses Catmull-Rom splines to estimate where the attacker was at the exact moment of the hit, not just the tick-boundary position
2. **Distance Calculation**: Compares the interpolated distance against Minecraft's maximum reach (3.0 blocks for survival, 5.0 for creative)
3. **Latency Compensation**: Accounts for network latency to avoid false positives

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = tighter reach threshold tolerance |
| Command | `/ac-reach` | Toggle on/off |

## Technical Details
The Catmull-Rom interpolation uses 4 position samples to create a smooth curve, providing sub-tick accuracy for reach measurements. This is significantly more accurate than simple tick-to-tick distance checks.