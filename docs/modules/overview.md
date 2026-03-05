# Modules Overview

Paradox AntiCheat includes **35 detection, prevention, and admin modules**, each independently toggleable and configurable.

## Module Categories

### Detection Modules
These modules actively monitor player behavior and flag suspicious activity.

| Module | Command | Default | Description |
|--------|---------|---------|-------------|
| Fly | `/ac-fly` | ON | Flight/hover hack detection |
| KillAura | `/ac-killaura` | ON | Combat bot detection |
| Reach | `/ac-reach` | ON | Extended reach detection |
| AutoClicker | `/ac-autoclicker` | ON | Click bot detection |
| Scaffold | `/ac-scaffold` | ON | Speed bridging detection |
| X-Ray | `/ac-xray` | ON | Mining hack detection |
| GameMode | `/ac-gamemode` | ON | Unauthorized gamemode changes |
| NameSpoof | `/ac-namespoof` | ON | Name manipulation detection |
| Self-Infliction | — | ON | Self-damage exploit detection |
| Vision | `/ac-vision` | ON | Aimbot/snap aim detection |
| SkinGuard | `/ac-skinguard` | ON | 4D/tiny/invisible skin detection |
| NoClip | — | ON | Phase/noclip through solid blocks |
| WaterWalk | — | ON | Walking on water (Jesus hack) |
| Step Hack | — | ON | Stepping up blocks without jumping |
| Timer | — | ON | Game speed manipulation |
| Blink | — | ON | Instant teleport/blink hacks |
| Anti-KB | — | ON | Anti-knockback (not moving after hit) |
| Criticals | — | ON | Always-critical hit exploits |
| Wall Hit | — | ON | Hitting through solid blocks |
| TriggerBot | — | ON | Auto-attack on target acquisition |

### Community & Moderation Modules (Tier 2)
These modules handle community management and staff tools.

| Module | Command | Default | Description |
|--------|---------|---------|-------------|
| Discord Integration | — | OFF | Webhook alerts for violations, bans, and kicks with colour-coded severity |
| Chat Protection | — | ON | Spam detection, ad filter, swear filter, caps limiter, mute system |
| Anti-Grief | — | ON | Anti-nuke, rapid placement detection, explosion logging |
| Evidence Replay | — | ON | Ring-buffer player action recording, auto-snapshots on violations |

### Prevention Modules
These modules actively prevent exploits.

| Module | Command | Default | Description |
|--------|---------|---------|-------------|
| Anti-Dupe | `/ac-modules antidupe` | OFF | 4-layer dupe prevention |
| Crash-Drop | `/ac-modules crashdrop` | OFF | Anti-crash-drop protection |
| Inv-Sync | `/ac-modules invsync` | OFF | Inventory snapshot sync |
| Illegal Items | — | ON | Enchantment, stack size, creative-only item scanning |

### Admin & Utility Modules
These modules provide server management tools.

| Module | Command | Default | Description |
|--------|---------|---------|-------------|
| AFK | `/ac-afk` | ON | Idle player tracking |
| World Border | `/ac-worldborder` | ON | Border enforcement |
| Lag Clear | `/ac-lagclear` | ON | Scheduled entity cleanup |
| PvP Manager | — | ON | PvP toggle system |
| Rate Limiter | `/ac-ratelimit` | OFF | Packet flood & DoS protection |
| Packet Monitor | `/ac-packetmonitor` | OFF | Packet frequency diagnostics |
| Container See | `/ac-containersee` | OFF | Admin inventory vision (action bar) |

## Sensitivity Scaling

All detection modules support a **sensitivity scale from 1 to 10**:

- **1-3**: Lenient — fewer false positives, may miss subtle cheats
- **4-6**: Balanced (default = 5) — good for most servers
- **7-10**: Strict — catches more cheats but may flag legitimate edge cases

Set sensitivity via:
```
/ac-modules <module> sensitivity <1-10>
```

Or via the Web UI's Modules page (detection modules only — server features show toggle-only controls).

## Toggling Modules

```
/ac-modules <module> on     # Enable a module
/ac-modules <module> off    # Disable a module
```

Or use `/ac-gui` → Module Management for a visual interface.
