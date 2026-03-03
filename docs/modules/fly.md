# Fly Detection

## Overview
Detects flight and hover hacks by analyzing player movement patterns, with comprehensive exemptions to reduce false positives.

## How It Works
1. **Surrounding Block Check**: Examines 9 blocks below the player (center + 8 surrounding). Only flags if the majority are air — avoids false positives near stairs, edges, and half-slabs.
2. **Velocity Analysis**: Monitors vertical and horizontal velocity — legitimate players fall or jump with predictable acceleration.
3. **Hover Time Tracking**: Counts consecutive suspicious ticks in the air before flagging.

## Exemptions
The following situations are automatically exempted to prevent false positives:
- **Creative/Spectator mode** — flying is legitimate
- **Elytra gliding** — `is_gliding` check
- **Swimming** — `is_in_water` check
- **Climbing** — ladders, vines, scaffolding
- **Trident Riptide** — tracked via trident use event
- **Knockback** — 2 seconds after taking damage (prevents flags from PvP/mob hits)
- **Slime/Honey blocks** — bouncing is legitimate air time
- **L4 Admins** — exempt from detection

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | 1-10 scale. Higher = stricter air-block majority threshold |
| Command | `/ac-fly` | Toggle on/off |

## Actions
All detections are routed through the [Violation Engine](violation-engine.md):
- **Severity 3** (MEDIUM) — flags with hover duration vs threshold
- Action hint: `setback` (teleport to last safe ground position)
- Evidence logged for `/ac-case` review