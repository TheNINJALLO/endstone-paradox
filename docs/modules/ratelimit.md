# Rate Limiter

## Overview
Detects and blocks packet flooding, with automatic DoS lockdown.

## How It Works
1. **Packet Rate Monitoring**: Counts all incoming packets per player per second
2. **Violation Tracking**: Multiple rate limit violations escalate to a kick
3. **DoS Detection**: If multiple players trigger rate limits simultaneously, the server enters lockdown mode
4. **Automatic Lockdown**: Non-admin players are kicked, and lockdown releases after 60 seconds

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Max Packets/s | 2000 | Bedrock sends ~500 normally |
| Violation Threshold | 20 | Violations before kick |
| DoS Player Threshold | 5 | Simultaneous violators to trigger lockdown |
| Command | `/ac-ratelimit` | Toggle on/off |

> **Note**: This module is OFF by default. Enable only after tuning thresholds for your server's player count and tick rate.