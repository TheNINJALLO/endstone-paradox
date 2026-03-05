# TriggerBot Detection

> Detects auto-attack bots that fire immediately when crosshair enters a target hitbox.

## How It Works

Tracks the time between a player's rotation entering a target's hitbox and the subsequent attack input. If the delay is consistently less than 100ms, it indicates a TriggerBot. Requires **4 out of 10** suspicious attacks in the analysis window before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Reaction threshold | <100ms (rotation → attack) |
| Suspicious ratio | 4/10 in analysis window |
| Level 4 exempt | Yes |

## Default State

**ON**
