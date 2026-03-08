# Report System

> **Module name:** `reportsystem` | **Command:** `/ac-reportsystem` | **Default:** OFF

In-game player reporting with a web-based staff queue.

## Features

- **`/ac-report <player> [reason]`** — Available to all players (no admin required)
- **Rate limiting** — Max 3 reports per player per 5 minutes
- **Auto-escalation** — Reports open >30 minutes automatically upgrade to `priority`
- **Status tracking** — `open` → `priority` → `claimed` → `resolved`
- **Web UI queue** — Staff can claim and resolve reports at `/reports`

## Report Lifecycle

1. Player submits via `/ac-report PlayerName cheating`
2. Report enters queue as `open`
3. After 30 min without action → auto-escalates to `priority`
4. Staff claims via web UI → `claimed`
5. Staff resolves → `resolved` with resolution note

## Web UI

Access the report queue at `/reports` in the web admin panel. Supports filtering by status and one-click claim/resolve.
