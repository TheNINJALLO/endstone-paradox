# Optional global database integration

Global synchronization is **disabled on new installations**. Configure an explicit HTTPS endpoint only if you intend to use that service. The plugin does not silently contact a default public API or restore the archived Python name-ban list.

```toml
[global_database]
enabled = false
api_url = ""
api_key = ""
sync_interval = 300
```

When enabled with an endpoint, the native worker uses `/api/servers/self-register` if a key is absent, then `/api/sync?since=...` with `X-API-Key`. A returned registration key and synchronization timestamp are persisted locally. The polling interval is at least 60 seconds. An enabled setting with no URL logs a warning and retains local bans.

## Identity and enforcement

Remote records with a valid numeric XUID can be cached by authenticated identity. Records categorized as bans can deny a matching player's join; revocation/removal records remove the cached ban. Name-only records are retained as review flags and cannot ban a player. Local operator-created legacy bans remain in place during migration.

This integration enforces an explicitly selected external ban policy; it does not make native observational checks create automatic bans. A player name alone, shared device or behavior report is not sufficient native proof.

Disabling synchronization does not delete cached XUID bans; those records still apply at join. Review retained policy when migrating or disconnecting from a service. See [migration](migration.md).

## Information sent

With an endpoint and key configured, healthy corroborated findings may be sent to `/api/report/batch` with player name, XUID, module, severity and evidence. Review the service's operation and data handling before enabling it. The release acceptance tests disabled external destinations and sent no live reports.

Discord is a separate optional HTTPS webhook configured under `[discord] webhook_url`. With its module enabled and a destination configured, it receives notifications for non-observational findings through the bounded integration worker. See [configuration](configuration.md).
