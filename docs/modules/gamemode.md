# GameMode Guard

## Overview
Instantly blocks unauthorized gamemode changes.

## How It Works
Monitors `PlayerGameModeChangeEvent` and cancels any gamemode change by players below the required clearance level.

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | N/A | Not applicable — this is a binary check |
| Command | `/ac-gamemode` | Toggle on/off |