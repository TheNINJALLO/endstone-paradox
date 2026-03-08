# Bot Detection

> **Module name:** `botdetection` | **Command:** `/ac-botdetection` | **Default:** OFF

3-layer bot detection system that identifies automated players through behavioral analysis.

## Detection Layers

### 1. Behavioral Entropy
Analyzes movement patterns using Shannon entropy. Bots tend to produce either perfectly uniform or artificially random movement — both distinguishable from human play.

### 2. Connection Patterns
Detects rapid join/leave cycling — a common pattern for bot swarms that join, perform an action, then disconnect.

### 3. Honeypot Blocks
Admin-placed invisible trap blocks. When a player interacts with a honeypot block, it's a strong signal they're using an automated client (no human would know the block exists).

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Enabled | `false` | Toggle with `/ac-botdetection` |
| Sensitivity | 5 | 1-10 scale — higher catches more bots but may flag edge cases |
