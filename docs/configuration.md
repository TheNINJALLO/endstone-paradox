# Configuration

Paradox Native uses `plugins/paradox/config.toml` and `plugins/paradox/paradox.db`. Stop the server before editing files and restart after TOML changes. Use commands or the native UI for supported runtime changes.

## New-install example

These are native settings, including optional integration and policy examples:

```toml
[web_ui]
enabled = true
host = "127.0.0.1"
port = 8080

[global_database]
enabled = false
api_url = ""
api_key = ""
sync_interval = 300

[discord]
webhook_url = ""

[afk]
timeout = 600
kick = false

[lagclear]
interval = 300
enabled_removal = false

[worldborder]
radius = 0
x = 0
z = 0

[gamemodepolicy]
survival = true
creative = true
adventure = true
spectator = true

[modules.gamemodepolicy]
enabled = false

[modules.landclaim]
enabled = false

[modules.gravesaver]
enabled = false
```

A zero world-border radius leaves the boundary inactive. AFK defaults to tips, and new-install scheduled entity removal requires `enabled_removal = true`. Existing lag-clear configurations retain their previous enabled behavior when that key is absent. Inspect migrated settings before starting the server.

## Which setting wins?

For module states, a persisted SQLite value takes precedence over `[modules.<name>].enabled`, which takes precedence over the native default. Use `/ac-modstate <module> on|off` to update the active and persisted state. Editing a TOML module default does not override an existing database value.

The enforcement mode is persisted in SQLite and changed with `/ac-mode soft|hard|logonly`. The default is `soft`. Runtime AFK intervals, lag-clear intervals and world-border commands also save database overrides. Check those overrides when changing their TOML defaults.

The Python sensitivity scale and remote threshold tuning do not control native enforcement. There is no native `/ac-modules <name> sensitivity <value>` command. Review each [module's actual behavior](modules/overview.md).

## Integrations and credentials

Global synchronization is off by default and requires an explicitly configured HTTPS `api_url`; there is no implicit public endpoint. Discord requires an HTTPS `webhook_url`. See [global integration](global-database.md) for its identity and data-sharing rules.

Web authentication uses `web-token.txt`, not the old Flask secret key or password sessions. Treat this token as full administration access and keep it out of logs, screenshots and repositories. See [web setup](webui.md).

## Storage and backups

The SQLite store retains legacy tables and adds native evidence, identity history, policies and audit records. Writes use a bounded worker queue, WAL, transactions and shutdown flushing. `/ac-debug-db` flushes the queue and reports persistence errors; investigate any error before relying on saved state.

Back up the complete data directory while the server is stopped, or use SQLite's consistent backup facility. Do not copy only a live `.db` file while ignoring its WAL. The migration backup is not a substitute for routine backups. See [migration and rollback](migration.md).
