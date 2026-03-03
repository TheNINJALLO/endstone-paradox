# Self-Infliction Detection

## Overview
Detects self-damage exploits where players attempt to damage themselves for unfair advantages (such as triggering totem of undying effects).

## How It Works
Monitors `ActorDamageEvent` and flags cases where the attacker and victim are the same entity.

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Command | Module toggle via `/ac-modules` | Toggle on/off |