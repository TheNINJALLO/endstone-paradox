# Anti-Dupe Module

## Overview
4-layer duplication prevention system that detects and prevents item duplication exploits.

## Detection Layers

### Layer 1: Bundle Blocking
Prevents bundles from being placed inside hoppers, dispensers, droppers, and crafters — a known duplication vector.

### Layer 2: Hopper Cluster Monitoring
- Tracks hopper placements near other hoppers
- Monitors item counts in hopper clusters periodically
- If items **increase** without a player adding them → dupe detected
- **Allows hopper clocks** — total item count in a clock stays constant (items just transfer back and forth)

### Layer 3: Piston Entity Monitoring
- Monitors entity spawn rates near active pistons
- Detects TNT, carpet, rail, and gravity block duplication
- Rapid entity spawning in a small area triggers an alert

### Layer 4: Packet Analysis
- Monitors `InventoryTransactionPacket` and `ContainerOpenPacket` packets
- Flags rapid-fire inventory transactions (dupe exploit signature)
- Detects suspicious container open/close cycling

## Web UI Integration
All detection events are logged to the **Anti-Dupe Monitor** page in the web UI, including:
- Event type and timestamp
- Player name and UUID
- Coordinates and dimension
- Detailed detection context

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Default State | OFF | Needs per-server tuning |
| Sensitivity | 5 | Higher = more frequent scans, tighter thresholds |
| Command | `/ac-modules antidupe` | Toggle on/off |