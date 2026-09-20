# Player utility commands

Each utility requires its `paradox.<command>` permission, granted to everyone by default. Some actions also need a server module enabled. Commands referring to your position, inventory or session require an in-game player.

| Command | Behavior |
| --- | --- |
| `/ac-gui`, `/ac-guiitem` | Open native controls or receive the menu compass; staff actions remain protected |
| `/ac-about` | Display native version, target Endstone and upstream review |
| `/ac-ping [player]` | Show ping and detection readiness; no target means yourself |
| `/ac-tps` | Show server TPS and milliseconds per tick |
| `/ac-home set\|delete\|list\|tp [name]` | Save/manage personal locations with fractional coordinates and dimension |
| `/ac-waypoint set\|delete\|list\|tp [name]` | Separate personal waypoint collection with the same storage rules |
| `/ac-tpa <player>`, `/ac-tpa accept\|deny` | Request teleport to another player; request expires after 60 seconds |
| `/ac-tpr [radius]` | Random safe destination in already loaded terrain; default radius 500, accepted range 16-10000 |
| `/ac-pvp [on\|off\|status]`, `/ac-pvptoggle [on\|off\|status]` | Personal PvP state; ten-second toggle cooldown and no changes during the fifteen-second combat interval |
| `/ac-pvp global` | Toggle global PvP; additionally requires clearance 4 or `paradox.settings` |
| `/ac-channels create\|join <name>`, `/ac-channels leave\|list` | Chat channel membership; channel names up to 32 characters |
| `/ac-chunkborders` | Toggle your chunk-border particles when the server module is enabled |
| `/ac-landclaim create <name> [radius]` | Create a claim at your location when enabled; radius 4-128, default 16 |
| `/ac-landclaim delete <name>`, `/ac-landclaim list` | Remove your named claim or list claims; staff can see more records |
| `/ac-landclaim trust\|untrust <name> <player>` | Change trust on your claim; the target player must be online |
| `/ac-report <player> <reason>` | Record a report when reportsystem is enabled; target online, thirty-second cooldown |

Homes and waypoints each allow 20 locations with names up to 48 characters. `/ac-home` returns to `default`; `/ac-waypoint` lists waypoints. Random teleport fails explicitly if no safe loaded destination exists. Teleports remain subject to applicable combat/dimension/server policies.

Claims allow five per player, names up to 32 characters and a four-block overlap buffer. Review the [landclaim module](../modules/landclaim.md) and [protection API limits](../migration.md); they do not promise complete hopper automation protection.

Use `/ac-modstate pvp on`, `/ac-modstate chunkborders on` or `/ac-modstate landclaim on` for the server module, subject to staff authorization. The short utility commands operate on player policy and are not substitutes for module toggles.
