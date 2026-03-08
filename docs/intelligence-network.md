# Global Intelligence Network

> The more Paradox servers participate, the smarter detection becomes for everyone.

## Overview

The Global Intelligence Network extends the [Global Ban Database](global-database.md) with crowd-sourced behavioral data. Every participating server contributes anonymized metrics, and all servers benefit from the aggregated insights.

## What Gets Shared

| Data Type | Format | Purpose |
|-----------|--------|---------|
| **Fingerprint hashes** | SHA-256 truncated (16 chars) | Cross-server alt/evasion detection |
| **Violation patterns** | `{module, metric, value}` | Crowd-sourced risk scoring |
| **Behavioral baselines** | Aggregated entropy/EMA averages | Shared "normal" thresholds |
| **Enforcement outcomes** | `{action, tier_counts}` | Adaptive threshold tuning |

> **Privacy:** No raw IPs, player names, or personal data are transmitted — only hashed identifiers and aggregated metrics.

## What You Get Back

| Intelligence | Description |
|-------------|-------------|
| **Flagged Fingerprints** | Fingerprints flagged by 2+ independent servers |
| **Recommended Thresholds** | Crowd-tuned sensitivity values per module |
| **Reputation Scores** | Per-fingerprint risk scores (0-100, where 100 = clean) |

## Configuration

```toml
[global_database]
enabled = true

# Intelligence Network settings
share_fingerprints = true   # Push fingerprint hashes to the network
share_telemetry = true      # Push violation/behavioral stats
auto_tune = false           # Auto-apply crowd-sourced thresholds
```

| Setting | Default | Description |
|---------|---------|-------------|
| `share_fingerprints` | `true` | Share fingerprint hashes for cross-server alt detection |
| `share_telemetry` | `true` | Share violation rates and behavioral metrics |
| `auto_tune` | `false` | Automatically apply crowd-sourced sensitivity recommendations |

## How Auto-Tune Works

When `auto_tune = true`, the system:

1. Pulls recommended thresholds from the API during each sync
2. Compares against current module sensitivities
3. Auto-adjusts modules that differ from the network recommendation
4. Logs all changes so admins can review

When `auto_tune = false` (default), threshold recommendations are still pulled and shown to admins via the Adaptive Check module — but not applied automatically.

## Graceful Degradation

The client is designed to work even if the API server doesn't support the new intelligence endpoints yet:
- `HTTP 404` responses are silently ignored
- Network errors are retried on the next sync cycle
- All intelligence data is optional — the plugin works fine without it
