# KillAura Detection

## Overview
Detects combat bot (KillAura/Forcefield) hacks using dynamic threshold adaptation.

## How It Works
1. **Facing Angle Validation**: Checks if the attacker is actually facing the target within a reasonable angle
2. **Attack Rate Analysis**: Monitors attacks per second — human players have natural variation
3. **Pattern Analysis**: Looks for perfectly timed, evenly spaced attacks (bot signature)
4. **Dynamic Thresholds**: Thresholds adapt based on server TPS and player latency to reduce false positives

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = stricter facing angle and rate checks |
| Command | `/ac-killaura` | Toggle on/off |

## Actions
- **Alert**: Notifies L4 admins with attack pattern details
- **Escalation**: Repeated violations trigger automatic punishment