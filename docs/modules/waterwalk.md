# WaterWalk / Jesus Detection

> Detects players standing on water without Frost Walker, ice, or lily pads.

## How It Works

Checks if a player is standing on water blocks without legitimate means (Frost Walker enchantment, ice blocks, or lily pads beneath them). Uses a **hitbox footprint check** — the player's ~0.6-wide foot rectangle is sampled at all 4 corners so that standing on solid block edges near water does not trigger a false positive. Requires **4 flags** before emitting a violation.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Flags required | 4 |
| Footprint width | ±0.3 blocks from center |
| Exemptions | Frost Walker boots, ice blocks, lily pads, solid block support |
| Level 4 exempt | Yes |

## Default State

**ON**
