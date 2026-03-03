# Moderation Commands

All moderation commands require appropriate [clearance level](security.md).

| Command | Description | Min. Clearance |
|---------|-------------|----------------|
| `/ac-op` | Authenticate as admin (set or enter password) | Anyone (sets L4) |
| `/ac-deop` | Remove admin status from a player | L4 |
| `/ac-ban <player> [reason]` | Ban a player from the server | L3 |
| `/ac-unban <player>` | Unban a player | L3 |
| `/ac-kick <player> [reason]` | Kick a player | L3 |
| `/ac-freeze <player>` | Freeze/unfreeze a player (prevent movement) | L3 |
| `/ac-vanish` | Toggle invisibility (admins only) | L3 |
| `/ac-lockdown [level]` | Toggle server lockdown (only high-clearance players can join) | L4 |
| `/ac-punish <player> <action>` | Punish a player (warn, kick, ban) | L3 |
| `/ac-tpa <player>` | Teleport to a player | L3 |
| `/ac-allowlist <add/remove> <player>` | Manage the server allowlist | L4 |
| `/ac-whitelist <add/remove> <player>` | Manage the whitelist | L4 |
| `/ac-opsec` | View security status and authentication info | L4 |
| `/ac-despawn` | Remove nearby entities | L3 |
| `/ac-modules <name> <on/off>` | Toggle any module on or off | L4 |
| `/ac-spooflog` | View name spoof detection logs | L3 |
| `/ac-command <cmd>` | Execute a server command as console | L4 |
| `/ac-prefix <prefix>` | Change the command prefix | L4 |
