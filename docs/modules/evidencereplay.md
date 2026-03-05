# Evidence Replay

> Ring-buffer player state recording with auto-snapshots on violations.

## Overview

The Evidence Replay module continuously records player state (position, rotation, actions) in a per-player ring buffer. When any detection module emits a violation, the replay buffer is automatically snapshotted and persisted to the database. Staff can then review exactly what happened before and during a violation.

## Features

| Feature | Description |
|---------|-------------|
| **Continuous Recording** | Captures player position, rotation, health, actions every tick |
| **Ring Buffer** | Configurable buffer depth (default 200 frames) — only keeps recent history |
| **Auto-Snapshot** | Automatically snapshots when any violation is emitted |
| **Action Tracking** | Records breaking, placing, attacking, chatting, moving actions |
| **Snapshot Summary** | Human-readable summaries showing distance traveled, actions taken, speed, violations |
| **Frame-by-Frame** | Staff can review individual frames from a snapshot |
| **Persistent Storage** | Snapshots saved to database (max 50 per player) |

## Usage

Snapshots are automatically taken whenever a violation is emitted. Staff can review via:

```
/ac-case <player>              # View recent violations (includes replay data)
/ac-debug-db logs replays      # View raw replay data
```

## Configuration

```
/ac-debug-db config replay_buffer_depth 200    # Frames per player
/ac-debug-db config replay_max_snapshots 50    # Max stored snapshots per player
```

## Default State

**ON** — Active by default, recording in the background.
