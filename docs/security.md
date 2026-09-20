# Security and staff clearance

Native handlers identify real player and console senders through Endstone's supported accessors and reject unrecognized senders. **Use v2.0.1:** the superseded v2.0.0 preview could mistake a wrapped player for the console. Connected-client acceptance verifies that ordinary players cannot change enforcement settings.

## Assigning staff

From the server console, with the player online:

```text
ac-setclearance "Player Name" 4
```

Clearance values range from 1 to 4. New players receive 1. Most moderation/evidence handlers accept level 3; settings/security changes generally require 4. A handler also accepts its explicitly checked Endstone permission. See [command permissions](commands/moderation.md) for exceptions and exact nodes.

Endstone operators receive registered staff permissions by default. Revoking Paradox clearance does not revoke Endstone operator status or permissions granted by another permissions plugin. `/ac-deop` removes your own Paradox clearance; targeting another player requires level 4 or `paradox.deop`.

`/ac-op <password>` only validates a previously stored legacy password hash. It does not create the first administrator or open the Python password form. Use console clearance assignment for new installations.

## Permission defaults

| Permission | Default | Meaning |
| --- | --- | --- |
| `paradox.use` | Everyone | Access to registered command entry points; handlers still authorize actions |
| `paradox.<utility>` | Everyone | Ordinary utilities: home, tpa, tpr, pvp, pvptoggle, channels, gui, guiitem, about, ping, tps, waypoint, chunkborders, report and landclaim |
| Registered staff command permissions | Operators | Administrative handlers check their specific node or staff clearance |
| `paradox.settings` | Operators | Native settings changes and privileged GUI controls |
| `paradox.alerts` | Operators | Receive finding notifications |
| `paradox.bypass` | Nobody | Explicit detection bypass; do not grant globally |

Some handlers share a permission instead of the command's name: inventory viewing uses `paradox.invsee`; inventory changes additionally require level 4 or `paradox.settings`; case/history/replay use `paradox.case`; clearance assignment and database diagnostics use `paradox.opsec`. Opening a GUI never grants the permissions required for its buttons.

## Administration boundaries

The dashboard's bearer token grants console-level access to supported Paradox commands. It is not a player clearance token. Protect it and the data directory, bind locally by default, and use an HTTPS reverse proxy or SSH tunnel for remote administration. See [web interface](webui.md).

`/ac-command enable|disable <command>` changes command availability for players below clearance 4. It is not an arbitrary console-command executor. `/ac-prefix` changes message text, not command registration names.

Allowlist detection exemptions, whitelist access policy, staff bans, AFK kicks, land/container restrictions and lockdown are administrative policies, distinct from automated cheating findings. Review [migration limits](migration.md) before enabling policies on an existing world.
