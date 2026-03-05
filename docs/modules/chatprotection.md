# Chat Protection

> Spam detection, advertising filter, profanity filter, caps limiter, and mute system.

## Overview

The Chat Protection module provides a comprehensive chat moderation suite. It processes all chat messages before they reach other players.

## Features

| Feature | Description |
|---------|-------------|
| **Spam Detection** | Detects repeated messages (similarity check) and message flooding (rate limiting) |
| **Advertising Filter** | Blocks IP addresses, URLs, and domain names in chat using regex patterns |
| **Swear/Profanity Filter** | Configurable word list with whole-word matching |
| **Caps Limiter** | Flags messages with excessive capitalization |
| **Mute System** | Timed or permanent mutes, persisted to database |
| **Violation Integration** | Emits violations to the violation engine for enforcement escalation |

## Mute Commands

```
# Mute a player (permanent)
/ac-punish <player> mute

# Unmute
/ac-punish <player> unmute
```

## Configuration

Set thresholds via database:
```
/ac-debug-db config chatprotection_spam_window 5.0
/ac-debug-db config chatprotection_spam_max 5
/ac-debug-db config chatprotection_caps_ratio 0.7
```

Add/remove swear words:
```
/ac-debug-db config chatprotection_swear_words ["word1", "word2"]
```

## Default State

**ON** — Active by default with sensible thresholds.
