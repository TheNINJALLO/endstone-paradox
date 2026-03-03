# Security & Clearance System

## Overview

Paradox uses a **4-level clearance system** instead of relying on Minecraft's built-in operator system. This prevents operator abuse and provides granular permission control.

## Clearance Levels

| Level | Name | Permissions |
|-------|------|-------------|
| **L1** | Default | Basic commands (home, tpr, pvp, channels) |
| **L2** | Moderate | Access to the GUI menu |
| **L3** | High | Moderation commands (ban, kick, freeze, vanish, teleport) |
| **L4** | Full Admin | Everything — module management, lockdown, config, exempt from all checks |

## Authentication

### Initial Setup
The first player to run `/ac-op` sets the admin password. The password is stored as a **SHA-256 hash** — it is never stored in plaintext.

### Logging In
```
/ac-op
```
A GUI form appears to enter the password. On successful authentication, the player is set to L4.

### Revoking Access
```
/ac-deop <player>
```
Reduces a player back to L1.

### Setting Levels
Clearance levels can be set via:
- **In-game**: `/ac-deop` (to L1) or `/ac-op` (to L4)
- **Web UI**: Permissions page — set any player to any level
- **Database**: Directly modify the `players` table

## Security Features

- **SHA-256 Password Hashing**: Passwords are never stored in plaintext
- **L4 Exemption**: Level 4 admins are exempt from all detection modules
- **Global Ban List**: 509 known cheaters from the original Paradox are checked on join
- **Lockdown Mode**: Only players at or above the lockdown level can join during lockdown
