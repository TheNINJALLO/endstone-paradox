# Lag Clear

## Overview
Scheduled entity cleanup to reduce server lag.

## How It Works
1. **Scheduled Clearing**: Removes ground item entities at configurable intervals
2. **Warning System**: 30-second countdown warning in chat before clearing
3. **Entity Types**: Primarily targets dropped items, configurable entity types

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Interval | Configurable | Time between clears |
| Command | `/ac-lagclear` | Toggle on/off |