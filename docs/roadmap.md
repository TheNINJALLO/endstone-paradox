# Roadmap

> Track our progress toward making Paradox the most comprehensive Bedrock anti-cheat available.

---

## 🔨 Tier 1 — In Progress

### Movement Validation Suite

| Detection | How It Works | Status |
|-----------|-------------|--------|
| **NoClip / Phase** | Ray-traces player movement path between ticks — if it passes through solid blocks, flag | 🔨 Building |
| **Jesus / WaterWalk** | Flags players standing on water without Frost Walker or lily pads | 🔨 Building |
| **Step Hack** | Detects stepping up full blocks without a jump flag in PlayerAuthInputPacket | 🔨 Building |
| **Timer Hack** | Tracks PlayerAuthInputPacket frequency — 20/s is normal; >22 = timer, <18 = slow-timer | 🔨 Building |
| **Blink / Teleport** | Flags position jumps >10 blocks between ticks without a server teleport event | 🔨 Building |

### Combat Validation Suite

| Detection | How It Works | Status |
|-----------|-------------|--------|
| **Anti-Knockback** | Tracks velocity after damage — if player doesn't move within 3 ticks of being hit, flag | 🔨 Building |
| **Criticals** | Tracks if player always gets critical hits (falling flag set without actually falling) | 🔨 Building |
| **Hit Through Walls** | Raycasts from attacker eye to victim — if any solid block blocks line of sight, flag | 🔨 Building |
| **TriggerBot** | Tracks time between crosshair entering target hitbox and attack — <50ms consistently = bot | 🔨 Building |

### Illegal Item Scanner

| Feature | Description | Status |
|---------|-------------|--------|
| **Enchantment Validation** | Detects illegal enchantment levels (Sharpness 32767, etc.) | 🔨 Building |
| **Stack Size Validation** | Flags items with impossible stack sizes | 🔨 Building |
| **Creative-Only Items** | Flags creative-only items in survival mode | 🔨 Building |
| **Auto-Remove** | Automatically removes illegal items with evidence logging | 🔨 Building |

---

## 📋 Tier 2 — Planned

| Feature | Description | Status |
|---------|-------------|--------|
| **Discord Integration** | Webhook alerts for bans, violations, and staff notifications with rich embeds | 📋 Planned |
| **Chat Protection** | Spam detection, advertising filter, swear filter, caps limiter, command throttle, mute system | 📋 Planned |
| **Anti-Grief / World Protection** | Anti-nuke (mass block break), explosion logging, lava/water tracking, build protection zones | 📋 Planned |
| **Evidence Replay** | Record player position + actions before each violation — staff can `/ac-replay` to investigate | 📋 Planned |

---

## 🔮 Tier 3 — Future

| Feature | Description | Status |
|---------|-------------|--------|
| **Analytics Dashboard** | Violation charts, map heatmaps, player risk scores, server health metrics in the web UI | 🔮 Future |
| **Bot Detection** | Behavioral entropy analysis, connection pattern analysis, honeypot blocks | 🔮 Future |
| **Player Report System** | `/report` command, web UI queue with priority, auto-escalation, staff claim/resolve | 🔮 Future |
| **Session Fingerprinting** | Device fingerprint → alt account detection, ban evasion tracking via Global Ban API | 🔮 Future |
| **Adaptive Check Frequency** | Clean players checked less often, flagged players checked every tick — saves resources | 🔮 Future |

---

## ✅ Completed

| Feature | Version | Description |
|---------|---------|-------------|
| Player Baseline (EMA) | v1.5.6 | Per-player behavioral profiling with Exponential Moving Averages |
| Speed Hack Detection | v1.5.7 | Position-delta tracking with 7.3 bps threshold |
| Multi-Target KillAura | v1.5.7 | Detects >2 unique targets in 0.5s window |
| Aimbot Acceleration | v1.5.7 | Rotation acceleration + pre-attack snap correlation |
| Backwards Scaffold | v1.5.7 | Block behind facing direction detection |
| Smart Lag Clear | v1.5.7 | Excludes name-tagged and NPC entities |
| Global Ban API | v1.5.5 | Zero-config cross-server ban synchronization |
| 4-Layer Anti-Dupe | v1.5.0 | Bundle, hopper, piston, and packet analysis |
