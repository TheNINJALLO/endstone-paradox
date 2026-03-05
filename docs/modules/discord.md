# Discord Integration

> Webhook alerts for violations, bans, and kicks — sent to Discord via colour-coded embeds.

## Overview

The Discord Integration module forwards anti-cheat events to one or more Discord channels via webhooks. All messages are sent from a **non-blocking background thread** with rate limiting to avoid Discord API throttling.

## Features

| Feature | Description |
|---------|-------------|
| **Violation Alerts** | Colour-coded embeds by severity (grey → blue → yellow → orange → red) |
| **Ban Notifications** | Rich embed when a player is banned (manual or auto) |
| **Kick Notifications** | Embed when a player is kicked |
| **Severity Filter** | Only sends alerts above a configurable minimum severity |
| **Rate Limiting** | Max 5 messages per 5 seconds to avoid Discord throttling |
| **Background Thread** | Non-blocking daemon thread — won't slow down the server |

## Configuration

Set the webhook URL in `config.toml`:

```toml
[discord]
webhook_url = "https://discord.com/api/webhooks/..."
min_severity = 3       # 1=Info, 2=Low, 3=Medium, 4=High, 5=Critical
send_bans = true
send_kicks = true
```

Or set via database:
```
/ac-debug-db config discord_webhook_url https://discord.com/api/webhooks/...
```

## Default State

**OFF** — Requires webhook URL configuration to function.
