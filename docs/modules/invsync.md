# Inventory Sync Module

## Overview
Prevents rejoin-based duplication by maintaining **DB-persisted inventory snapshots** and comparing against the player's inventory on rejoin.

## How It Works

### Periodic Snapshots
Every 5 seconds, the module snapshots each online player's inventory item counts and stores them in the SQLite database. This data survives server restarts (unlike the original JS version which used volatile dynamic properties).

### Rejoin Comparison
When a player joins:
1. Wait 1 second for their inventory to fully load
2. Compare current inventory counts against the stored snapshot
3. If any item type has **more** items than the snapshot, flag the excess as potentially duped

### Example
A player has `64 diamonds` when they disconnect. They exploit a dupe glitch. When they rejoin with `128 diamonds`, InvSync detects the `+64 diamond` anomaly and alerts admins.

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Default State | OFF | Needs tolerance tuning |
| Sensitivity | 5 | Higher = stricter item diff tolerance |
| Snapshot Interval | 5 seconds | How often to capture inventory state |
| Command | `/ac-modules invsync` | Toggle on/off |