# Scaffold Detection

## Overview
Detects speed bridging / scaffold hacks by analyzing block placement patterns.

## How It Works
1. **Air-Below Filtering**: Only analyzes placements where the block below is air (bridging)
2. **Axis Pattern Analysis**: Detects placements that follow a perfectly straight line on one axis at high speed
3. **Exclusions**: Sneaking players and farmland interactions are excluded to avoid false positives

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = stricter bridge speed and pattern thresholds |
| Command | `/ac-scaffold` | Toggle on/off |