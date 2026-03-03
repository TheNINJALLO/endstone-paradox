# AutoClicker Detection

## Overview
Enhanced multi-platform autoclicker detection with air-click tracking and click consistency analysis.

## Detection Layers

### Layer 1: Per-Platform CPS Tracking
Monitors clicks per second (CPS) against platform-specific thresholds:

| Platform | Default CPS Cap | Detection Method |
|----------|-----------------|------------------|
| **PC** (Windows) | 22 CPS | Mouse clicks (butterfly/jitter ~20 max) |
| **Mobile** (Android/iOS) | 16 CPS | Touch taps (multi-finger ~14 max) |
| **Console** (Xbox/PS/Switch) | 12 CPS | Controller trigger (~10 max) |

Platform is detected automatically from the player's `DeviceOS` sent during login.

### Layer 2: Air-Click Tracking
Monitors `PlayerAuthInputPacket` for the LeftClick input flag (bit 0x4). This detects autoclickers even when the player is **not hitting any entity** — just clicking air.

The same CPS thresholds apply to air clicks as entity hits.

### Layer 3: Click Consistency Analysis
Human clicks have natural variance in timing. Autoclickers produce inhumanly consistent click intervals.

The module calculates the **coefficient of variation** (CV = stddev / mean) of click intervals:
- **CV > 0.15**: Normal human variance ✅
- **CV 0.08-0.15**: Borderline — flagged at higher sensitivity
- **CV < 0.08**: Suspiciously consistent — likely a bot 🚨

Requires at least 8 clicks in the window to run analysis.

## Sensitivity Scaling

| Sensitivity | CPS Factor | CV Threshold |
|-------------|-----------|--------------|
| 1 (lenient) | ×1.5 (PC=33) | 0.04 (only catches perfect bots) |
| 5 (default) | ×1.0 (PC=22) | 0.08 |
| 10 (strict) | ×0.5 (PC=11) | 0.15 (catches sophisticated clickers) |

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | 1-10 scale — affects both CPS cap and CV threshold |
| Command | `/ac-autoclicker` | Toggle on/off |
| `cps_pc` | 22 | Custom PC CPS cap (set via DB) |
| `cps_mobile` | 16 | Custom Mobile CPS cap (set via DB) |
| `cps_console` | 12 | Custom Console CPS cap (set via DB) |

## Actions
- **CPS Exceeded**: Attack cancelled, admin alert with CPS count, cap, and platform
- **Consistency Flag**: Admin alert with CV value, effective CPS, and platform
- **Air-Click Flag**: Admin alert noting air-clicking with CPS and platform