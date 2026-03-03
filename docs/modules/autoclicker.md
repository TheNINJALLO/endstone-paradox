# AutoClicker Detection

## Overview
Detects click bots using sliding-window CPS (clicks per second) tracking.

## How It Works
1. **CPS Tracking**: Counts attacks within a sliding time window
2. **Human Pattern Analysis**: Human clicks have natural variance in timing — perfectly consistent CPS indicates automation
3. **Configurable Threshold**: Default threshold is set for legitimate butterfly/jitter clicking

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = lower CPS threshold |
| Command | `/ac-autoclicker` | Toggle on/off |