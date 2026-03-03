# Reach Detection

## Overview
Detects extended reach hacks using **Catmull-Rom cubic interpolation** for accurate distance measurement, with proper attacker/victim event mapping and latency tolerance.

## How It Works
1. **Correct Combat Mapping**: Uses `event.damager` as the attacker and `event.actor` as the victim for accurate distance measurement
2. **Position Interpolation**: Uses Catmull-Rom splines to estimate where the attacker was at the exact moment of the hit, not just the tick-boundary position
3. **Distance Calculation**: Compares the interpolated distance against the maximum reach (4.5 blocks base + 0.5 latency tolerance)
4. **Latency Tolerance**: Adds a configurable extra distance (default +0.5 blocks) to account for network latency

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = tighter reach threshold tolerance |
| Latency Tolerance | 0.5 blocks | Extra distance allowance for laggy players |
| Command | `/ac-reach` | Toggle on/off |

Latency tolerance can be adjusted globally via the database: `config.latency_tolerance`

## Actions
All detections are routed through the [Violation Engine](violation-engine.md):
- **Severity 3** (MEDIUM) — flags with measured distance vs maximum
- Illegal hits are cancelled
- Evidence logged for `/ac-case` review

## Technical Details
The Catmull-Rom interpolation uses 4 position samples to create a smooth curve, providing sub-tick accuracy for reach measurements. This is significantly more accurate than simple tick-to-tick distance checks. Falls back to linear interpolation when fewer than 4 samples are available.