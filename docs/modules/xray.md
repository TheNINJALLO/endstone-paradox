# X-Ray Detection

## Overview
Detects mining hacks using **weighted suspicion scoring** with multiple detection factors.

## How It Works
1. **Vein-Jumping Detection**: Flags players who mine directly from one ore vein to another without mining stone in between
2. **Hidden Ore Detection**: Checks if mined ores were visible from any surface — x-ray users mine ores surrounded by stone
3. **Ore Ratio Analysis**: Compares the player's ore-to-stone ratio against statistical norms
4. **Suspicion Decay**: Suspicion points decay over time — one lucky find won't trigger a flag
5. **Graduated Escalation**: Alert → Priority Alert → Freeze + Admin notification

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = faster suspicion accumulation |
| Command | `/ac-xray` | Toggle on/off |

## Scoring
Each detection factor adds weighted points to a player's suspicion score:
- Hidden ore mined: +3 points
- Vein jump detected: +5 points
- Abnormal ore ratio: +2 points
- Points decay: -1 per minute