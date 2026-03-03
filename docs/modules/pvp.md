# PvP Manager

## Overview
Per-player PvP toggle system with combat tagging and combat log detection.

## How It Works
1. **PvP Toggle**: Players can enable/disable PvP for themselves via `/ac-pvp`
2. **Combat Tagging**: When a player attacks another, both are "combat tagged" for a duration
3. **Combat Log Detection**: If a combat-tagged player disconnects, admins are alerted

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Command | `/ac-pvp` | Toggle PvP for yourself |