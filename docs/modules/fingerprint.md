# Session Fingerprinting

> **Module name:** `fingerprint` | **Command:** `/ac-fingerprint` | **Default:** OFF

Device-based fingerprinting for alt account detection and ban evasion tracking.

## How It Works

On each player join, the module:

1. **Collects metadata** — IP address, device OS, device ID, XUID
2. **Creates a composite hash** — SHA-256 of sorted components, truncated to 16 characters
3. **Cross-checks locally** — Compares against all stored fingerprints for alt accounts
4. **Cross-checks globally** — Checks the Global Intelligence Network for flagged fingerprints
5. **Checks ban evasion** — If any linked account is banned, auto-kicks the player

## Alerts

| Event | Severity | Action |
|-------|----------|--------|
| Alt account detected | 2 | Admin alert with linked account names |
| Ban evasion | 5 | Admin alert + auto-kick |
| Globally flagged fingerprint | 3 | Admin alert from Intelligence Network |
| Low global reputation (<30) | 2 | Admin alert with score |

## Global Intelligence Integration

When the Intelligence Network is enabled (`share_fingerprints = true`), fingerprints are:
- **Pushed** to the Global API on each join (hashed, no PII)
- **Checked** against globally flagged fingerprints from other servers
- **Scored** with a reputation value (0-100) based on cross-server history
