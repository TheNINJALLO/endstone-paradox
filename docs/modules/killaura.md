# KillAura Detection

## Overview
Detects combat bot (KillAura/Forcefield) hacks using dynamic threshold adaptation and proper attacker/victim event mapping.

## How It Works
1. **Correct Combat Mapping**: Uses `event.damager` as the attacker and `event.actor` as the victim — ensures distance and facing checks measure the real attacker-to-victim relationship
2. **Distance Check**: Measures 3D distance between attacker and victim with configurable latency tolerance (+0.5 blocks default)
3. **Facing Angle Validation**: Checks if the attacker is actually facing the target within a reasonable angle
4. **Attack Rate Analysis**: Monitors attacks per second — human players have natural variation
5. **Pattern Analysis**: Looks for perfectly timed, evenly spaced attacks (bot signature) using interval difference analysis
6. **Dynamic Thresholds**: Thresholds adapt based on sensitivity settings to reduce false positives

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = stricter facing angle and rate checks |
| Latency Tolerance | 0.5 blocks | Extra distance allowance for laggy players |
| Command | `/ac-killaura` | Toggle on/off |

Latency tolerance can be adjusted globally via the database: `config.latency_tolerance`

## Actions
All detections are routed through the [Violation Engine](violation-engine.md):
- **Severity 3** (MEDIUM) — flags with reasons (dist, angle, rate, pattern)
- Enforcement determined by current mode and cumulative score
- Evidence logged with attack details for `/ac-case` review