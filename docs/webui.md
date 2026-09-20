# Native web interface

The native dashboard replaces the archived Python/Flask interface. It shows online players, ping and detection health, all module switches, recent evidence and a Paradox command field. Historical screenshots and old pages for password sessions, sensitivity tuning and report claim/resolve do not describe this interface.

## Connect

1. Start the plugin with `[web_ui] enabled = true`.
2. On the server machine, open `http://127.0.0.1:8080` (the new-install default).
3. Read `plugins/paradox/web-token.txt` locally and enter it in the Access token field.
4. Select **Connect**. The dashboard refreshes approximately every five seconds.

The token grants full administration of supported Paradox commands. It is held in page memory; reloading requires entering it again. A successful command submission means it was queued. Its result or failure appears in the server console, and the dashboard reflects subsequent state updates.

Existing configured host/port values are preserved. For remote access, use an SSH tunnel to localhost or an HTTPS reverse proxy. Do not expose a plaintext administration connection over an untrusted network. To rotate a token, stop Endstone, remove only `plugins/paradox/web-token.txt`, and restart; the plugin generates a new token. Rotation also changes the salt used by optional device fingerprint records.

## HTTP API

The dashboard shell (`/` and `/app.js`) is public. Both API routes require `Authorization: Bearer <token>`.

| Request | Result |
| --- | --- |
| `GET /api/status` | JSON snapshot containing version, TPS, players, modules, evidence, mode and protocol support |
| `POST /api/command` with `{"command":"ac-modules"}` | `202` when queued; execution occurs on the server thread |

Missing or invalid credentials return `401`. Invalid JSON/command input returns `400`; a full command queue returns `429`. Commands must begin with `ac-`, contain no line breaks or NULs, and fit the 1,024-character limit. The queue holds at most 32 commands; HTTP bodies are limited to 8,192 bytes. Player-only commands still require a player and cannot acquire one from a web request.

The native HTTP server, SQLite worker and HTTPS integration worker use bounded queues. There is no Python Flask process to install for this plugin. See [configuration](configuration.md) and [security](security.md).
