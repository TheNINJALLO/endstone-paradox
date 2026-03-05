# Timer Hack Detection

> Detects game speed manipulation via packet frequency analysis.

## How It Works

Tracks the frequency of PlayerAuthInputPacket per second. Normal Bedrock clients send ~20 packets/second. Fast-timer hacks send >23 pps, slow-timer sends <15 pps. Uses a sliding window of 4 samples for accuracy.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Normal frequency | ~20 pps |
| Fast-timer threshold | >23 pps |
| Slow-timer threshold | <15 pps |
| Windows analyzed | 4 |
| Level 4 exempt | Yes |

## Default State

**ON**
