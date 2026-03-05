# Roadmap

> Track our progress toward making Paradox the most comprehensive Bedrock anti-cheat available.

---

## ✅ Tier 1 — Movement, Combat & Item Protection — Complete

### Movement Validation Suite

| Detection | How It Works | Status |
|-----------|-------------|--------|
| **NoClip / Phase** | Ray-traces player movement path between ticks — if it passes through solid blocks, flag | ✅ Complete |
| **Jesus / WaterWalk** | Flags players standing on water without Frost Walker or lily pads | ✅ Complete |
| **Step Hack** | Detects stepping up full blocks without a jump flag in PlayerAuthInputPacket | ✅ Complete |
| **Timer Hack** | Tracks PlayerAuthInputPacket frequency — 20/s is normal; >22 = timer, <18 = slow-timer | ✅ Complete |
| **Blink / Teleport** | Flags position jumps >10 blocks between ticks without a server teleport event | ✅ Complete |

### Combat Validation Suite

| Detection | How It Works | Status |
|-----------|-------------|--------|
| **Anti-Knockback** | Tracks velocity after damage — if player doesn't move within 3 ticks of being hit, flag | ✅ Complete |
| **Criticals** | Tracks if player always gets critical hits (falling flag set without actually falling) | ✅ Complete |
| **Hit Through Walls** | Raycasts from attacker eye to victim — if any solid block blocks line of sight, flag | ✅ Complete |
| **TriggerBot** | Tracks time between crosshair entering target hitbox and attack — <50ms consistently = bot | ✅ Complete |

### Illegal Item Scanner

| Feature | Description | Status |
|---------|-------------|--------|
| **Enchantment Validation** | Detects illegal enchantment levels (Sharpness 32767, etc.) | ✅ Complete |
| **Stack Size Validation** | Flags items with impossible stack sizes | ✅ Complete |
| **Creative-Only Items** | Flags creative-only items in survival mode | ✅ Complete |
| **Auto-Remove** | Automatically removes illegal items with evidence logging | ✅ Complete |

---

## ✅ Tier 2 — Community & Moderation — Complete

| Feature | Description | Status |
|---------|-------------|--------|
| **Discord Integration** | Webhook alerts for bans, violations, and staff notifications with colour-coded severity embeds. Rate-limited background thread sender. | ✅ Complete |
| **Chat Protection** | Spam detection (flood + repeat), advertising filter (IPs/URLs/domains), swear/profanity filter (configurable word list), caps limiter, mute system with timed/permanent support | ✅ Complete |
| **Anti-Grief / World Protection** | Anti-nuke (mass block break detection), rapid placement rate-limit, explosion logging (TNT/creeper audit trail), configurable thresholds | ✅ Complete |
| **Evidence Replay** | Ring-buffer recording of player state (position, rotation, actions) every tick. Auto-snapshots on violations. Staff can review replay frames, get summaries, and filter by player | ✅ Complete |

---

## ⚡ Tier 3 — Intelligence & Analytics — In Progress

| Feature | Description | Status |
|---------|-------------|--------|
| **Analytics Dashboard** | Violation charts, map heatmaps, player risk scores, server health metrics in the web UI | 🔨 Building |
| **Bot Detection** | Behavioral entropy analysis, connection pattern analysis, honeypot blocks | 🔨 Building |
| **Player Report System** | `/report` command, web UI queue with priority, auto-escalation, staff claim/resolve | 🔨 Building |
| **Session Fingerprinting** | Device fingerprint → alt account detection, ban evasion tracking via Global Ban API | 🔨 Building |
| **Adaptive Check Frequency** | Clean players checked less often, flagged players checked every tick — saves resources | 🔨 Building |

---

## 📋 Completed Milestones

| Feature | Version | Description |
|---------|---------|-------------|
| Tier 2 Complete | v1.6.1 | Discord webhooks, chat protection, anti-grief, evidence replay |
| Tier 1 Complete | v1.6.0 | 10 new detection modules (movement + combat + illegal items) |
| ContainerSee Overhaul | v1.6.1 | Action bar display, player inventory vision, container identification |
| Web UI Modules Redesign | v1.6.1 | Two-section layout: detection modules with sliders, features with toggle-only |
| Player Baseline (EMA) | v1.5.6 | Per-player behavioral profiling with Exponential Moving Averages |
| Speed Hack Detection | v1.5.7 | Position-delta tracking with 7.3 bps threshold |
| Multi-Target KillAura | v1.5.7 | Detects >2 unique targets in 0.5s window |
| Aimbot Acceleration | v1.5.7 | Rotation acceleration + pre-attack snap correlation |
| Backwards Scaffold | v1.5.7 | Block behind facing direction detection |
| Smart Lag Clear | v1.5.7 | Excludes name-tagged and NPC entities |
| Global Ban API | v1.5.5 | Zero-config cross-server ban synchronization |
| 4-Layer Anti-Dupe | v1.5.0 | Bundle, hopper, piston, and packet analysis |
