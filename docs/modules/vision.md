# Vision / Aimbot Detection

## Overview
Detects aimbot and snap-aim hacks by analyzing rotation patterns.

## How It Works
1. **Rotation Snap Analysis**: Counts instances where a player's look direction snaps to a target with inhuman precision
2. **Turn Speed Check**: Monitors angular velocity — instant 180° turns are suspicious
3. **Pattern Accumulation**: Single snaps are ignored; repeated/consistent snaps accumulate suspicion

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = more sensitive to rotation snaps |
| Command | `/ac-vision` | Toggle on/off |