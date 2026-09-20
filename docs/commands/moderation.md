# Moderation and administration commands

Use `/` in chat and omit it in the console. Quote player names containing spaces. **L3 / node** below means clearance at least 3 **or** that checked Endstone permission; L4 works the same way. Operators receive registered staff permissions by default. Authorized console calls do not need player clearance. See [security](../security.md).

| Command | Behavior | Authorization |
| --- | --- | --- |
| `/ac-setclearance <player> <1..4>` | Assign clearance to an online player | L4 / `paradox.opsec` |
| `/ac-op <password>` | Validate an existing legacy password hash; no new-admin setup | Player, valid legacy password |
| `/ac-deop [player]` | Reset Paradox clearance to 1 | Self, or L4 / `paradox.deop` for another player |
| `/ac-ban <player> [reason]` | Persist a manual local ban and disconnect the online target | L3 / `paradox.ban` |
| `/ac-unban <name-or-UUID>` | Remove matching local bans; offline records supported | L3 / `paradox.unban` |
| `/ac-kick <player> [reason]` | Disconnect an online target | L3 / `paradox.kick` |
| `/ac-freeze <player>` | Toggle movement freeze for an online target | L3 / `paradox.freeze` |
| `/ac-punish <player> <action> [reason]` | `warn`, `mute`, `kick`, `ban`, `tempban` or `freeze`; mute is 10 minutes, tempban is 1 hour | L3 / `paradox.punish` |
| `/ac-vanish` | Toggle invisibility and name-tag hiding for yourself | L3 / `paradox.vanish`; player only |
| `/ac-lockdown on\|off [kick]` | Restrict new joins; retain current players unless `kick` is explicit | L4 / `paradox.lockdown` |
| `/ac-allowlist add\|remove <player>`, `/ac-allowlist list` | Manage detection exemptions using stored identity | L4 / `paradox.allowlist` |
| `/ac-whitelist add\|remove <player>`, `/ac-whitelist list\|on\|off` | Manage and enable server access policy | L4 / `paradox.whitelist` |
| `/ac-opsec [player]`, `/ac-whois [player]` | Review stored player records; a target argument must be online | L3 / `paradox.opsec` |
| `/ac-invsee <player>` | Inspect an online player's inventory | L3 / `paradox.invsee` |
| `/ac-inventory-editor <player> <slot> clear\|<item> [amount]` | Change an online player's slot; amount 1-64 | L3 / `paradox.invsee`, plus L4 / `paradox.settings` |
| `/ac-invclone <player>` | Copy an online player's inventory into your own | Same two checks as inventory editing; player only |
| `/ac-rank <player> <rank>` | Set an online player's score-tag rank | L3 / `paradox.rank` |
| `/ac-transfer <player> <host> [port]` | Transfer an online player; default port 19132 | L3 / `paradox.transfer` |
| `/ac-switch-game-mode <0..3> [player]` | Request server game-mode change, subject to policy; target defaults to self | L4 / `paradox.settings` |
| `/ac-broadcast <message>` | Broadcast to the server | L3 / `paradox.broadcast` |
| `/ac-environment time <value>` | `sunrise`, `day`, `noon`, `sunset`, `night` or `midnight` | L4 / `paradox.settings` |
| `/ac-environment weather <value>` | `clear`, `rain` or `thunder` | L4 / `paradox.settings` |
| `/ac-despawn [item\|arrow\|xp_orb] [radius]` | Remove eligible unnamed drops; player-centered radius defaults to 100; console cleanup has no player center | L3 / `paradox.despawn` |
| `/ac-command enable\|disable <command>` | Set availability for players below clearance 4 | L4 / `paradox.command` |
| `/ac-prefix <text>` | Change the message prefix, not command names | L4 / `paradox.prefix` |
| `/ac-debug-db` | Flush persistence and report errors | L4 / `paradox.opsec` |
| `/ac-spooflog` | Read stored spoof log records | L3 / `paradox.spooflog` |

Allow/whitelist additions can target previously joined offline players because identity history exists. A never-seen name cannot be authenticated this way. Manual bans and other online-target commands require a connected target unless noted above.

Moderating equal/higher-clearance targets requires `paradox.settings` in addition to the action's authorization. Vanish does not remove player-list entries or suppress every actor packet. Despawn excludes protected/named drops; review it before use.

See [module controls](toggles.md), [evidence and mode commands](violation.md) and [player utilities](utility.md).
