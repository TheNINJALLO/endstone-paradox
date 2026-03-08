# Adaptive Check Frequency

> **Module name:** `adaptivecheck` | **Command:** `/ac-adaptivecheck` | **Default:** OFF

Dynamically adjusts how often detection modules check each player based on their risk tier.

## Risk Tiers

| Tier | Condition | Check Multiplier |
|------|-----------|-----------------|
| **Low** | Violation score < 2.0 | 2× interval (less frequent) |
| **Medium** | Score 2.0 – 8.0 | 1× normal |
| **High** | Score > 8.0 | 0.5× interval (more frequent) |

## How It Works

Every 10 seconds, the module:

1. Calculates each online player's violation score from the engine
2. Assigns a risk tier (low / medium / high)
3. Adjusts all detection module intervals based on the highest active tier
4. Alerts admins when a player's tier escalates

## Benefits

- **Resource optimization** — Clean servers with no flagged players run checks at half frequency
- **Faster detection** — Flagged players are checked twice as often
- **Automatic** — No manual configuration needed

## Global Intelligence Integration

When enabled, pushes tier distribution telemetry (high-risk ratios, tier counts) to the Global API for crowd-sourced analysis.
