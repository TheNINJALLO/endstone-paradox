# All 54 native modules

These are the Paradox 2.0.1 defaults for a new installation. Persisted settings take precedence. Modules include observations, validation, policies and utilities; enabling a module does not imply it can punish a player. Review [enforcement and lag recovery](../violation-engine.md), [module controls](../commands/toggles.md) and [migration limits](../migration.md).

| Module | Kind | Default | Native behavior |
| --- | --- | --- | --- |
| [fly](fly.md) | movement | On | Speed/hover observations only; movement/terrain/effect recovery gate. |
| [noclip](noclip.md) | movement | On | Stone/bedrock overlap observation only; no unloaded-chunk collision verdict. |
| [waterwalk](waterwalk.md) | movement | On | Liquid-surface observation only; swimming and effects suspend movement analysis. |
| [stephack](stephack.md) | movement | On | Vertical-step observation only; slabs, moving blocks and reconciliation cannot prove cheating. |
| [timer](timer.md) | movement | On | Three healthy five-second windows of accelerated client time; gaps, bursts, duplicate/reordered ticks reset evidence. A retained session clock exempts gradual backlog recovery until caught up. Slow input is never flagged. |
| [blink](blink.md) | movement | On | Position-discontinuity observation only; teleports, joins and chunk availability reset history. |
| [killaura](killaura.md) | combat | On | Behind-view hit observation only; interpolation/input devices are not proof. |
| [reach](reach.md) | combat | On | Four excessive melee hits beyond conservative distance plus RTT/speed allowance. Attacker and target must be healthy; indirect/projectile/thorns damage, non-player target geometry and extended/unknown weapons are excluded. |
| [autoclicker](autoclicker.md) | combat | On | High attack-rate observation only, never a click-cadence ban. |
| [antikb](antikb.md) | combat | On | Server knockback displacement review only; collision/resistance can explain small movement. |
| [criticals](criticals.md) | combat | On | Airborne attack observation only; jump apex/effects are not punished. |
| [wallhit](wallhit.md) | combat | On | Bounded loaded-terrain line-of-sight review, limited to known full solid blocks. Observation only. |
| [triggerbot](triggerbot.md) | combat | On | Regular attack cadence observation only; controller/held-input behavior is not proof. |
| [vision](vision.md) | combat | On | Shares the conservative line-of-sight review. Observation only. |
| [scaffold](scaffold.md) | building | On | Neighbor support review for block placement. Observation only; custom placement tools are legitimate. |
| [xray](xray.md) | building | On | Ore-ratio review only; veins, exposed ore and custom worlds are not punished. |
| [gamemode](gamemode.md) | policy | On | Compatibility setting: server-authorized mode changes reset movement history and are accepted. Explicit restrictions use gamemodepolicy. |
| [namespoof](namespoof.md) | validation | On | Duplicate online display-name review; identities remain UUID/XUID based. |
| [selfinfliction](selfinfliction.md) | combat | On | Self-attributed direct melee review only. Reflected/indirect damage is excluded. |
| [skinguard](skinguard.md) | validation | On | Decoded image consistency review only; no bans for transparency, persona or marketplace geometry. |
| [illegalitems](illegalitems.md) | inventory | On | Overstack review only; custom plugin items are not destroyed. |
| [afk](afk.md) | management | On | Monotonic inactivity tracking; default tips only. Optional configured kick requires healthy connection; legacy timeout is preserved. |
| [worldborder](worldborder.md) | management | On | Explicit circular boundary policy permits movement back inward when already outside; legacy center fields preserved. |
| [lagclear](lagclear.md) | management | On | Scheduled administrative cleanup with warning; named/unlimited/protected drops excluded. New installs require explicit removal configuration. |
| [pvp](pvp.md) | management | On | Global/personal policy includes projectile attribution, ten-second toggle cooldown, fifteen-second combat interval. Disconnect never bans. |
| [ratelimit](ratelimit.md) | network | Off | Traffic observation only; BDS transport limits remain authoritative. Lag recovery prevents burst punishment. |
| [packetmonitor](packetmonitor.md) | network | Off | Traffic counts and review evidence; no packet-size/count auto-ban. |
| [containersee](containersee.md) | inventory | Off | Staff view of looked-at player inventory and container identification through the public API. No raw block-container NBT access. |
| [antidupe](antidupe.md) | inventory | Off | Inventory delta/NBT-hash audit. No snapshot rollback, item purge or automatic duplication accusation. |
| [crashdrop](crashdrop.md) | inventory | Off | Negative server item quantity may cancel a drop. No huge-stack or custom-NBT ban heuristic. |
| [invsync](invsync.md) | inventory | Off | Current inventory deltas and complete item-NBT hashes, including shulkers. Never compares an old snapshot as proof for removing items. |
| [discord](discord.md) | integration | On | Bounded asynchronous HTTPS webhook for non-observational findings; configured destination required. |
| [chatprotection](chatprotection.md) | chat | On | Rolling one-second chat/command windows, duplicate-message control and legacy mutes. Rate control pauses during recovery; no anti-cheat escalation. |
| [antigrief](antigrief.md) | building | On | High block-action rate review only; enchantments and building tools do not trigger automatic punishment. |
| [evidencereplay](evidencereplay.md) | evidence | On | Bounded player position/ping/health ring; latest replay stored separately from 100-entry history and 50-entry recent list. |
| [adaptivecheck](adaptivecheck.md) | evidence | Off | Records connection baselines. It never lowers enforcement thresholds from lagging samples or untrusted crowd data. |
| [botdetection](botdetection.md) | evidence | Off | Explicit configured honeypot interaction observation only; no automatic bot ban. |
| [reportsystem](reportsystem.md) | evidence | Off | Player reports with cooldown; reports are evidence for staff, never automatic punishments. |
| [fingerprint](fingerprint.md) | evidence | Off | Salted device hash for review. Shared devices and families are not banned; raw device IDs are not persisted. |
| [aimbotmonitor](aimbotmonitor.md) | combat | On | View-change observation only; mouse/controller snaps are not proof of aiming assistance. |
| [anticrash](anticrash.md) | network | On | Typed protocol-2193 decoding with byte, element and depth budgets. Known malformed inspected packets may cancel; budget excess is fail-open, never a ban. |
| [autototem](autototem.md) | inventory | On | Rapid totem inventory-change review only; no punishment for pickup, lag or custom inventory tools. |
| [containerlock](containerlock.md) | policy | Off | Owner locks and legacy migration; adjacent chests protected; explosions/flows/piston envelope handled. Hopper API limitation documented. |
| [deathcoords](deathcoords.md) | management | On | Fractional death coordinates and dimension are persisted and shown. |
| [dimensionlock](dimensionlock.md) | policy | Off | Explicit cross-dimension teleport/portal restriction; transitions always reset detection. |
| [pathingmonitor](pathingmonitor.md) | movement | On | Retained setting; robotic-pathing punishment removed. Straight movement and constant yaw are normal. |
| [hotbarcheck](hotbarcheck.md) | validation | On | Slot 0 through 8; validates selection only when should_select_slot is true. Invalid selection cancels without ban. |
| [invalidmovementvector](invalidmovementvector.md) | validation | On | Non-finite and out-of-range input axes can cancel; independent diagonal axes of 1,1 are accepted. |
| [inventorymovement](inventorymovement.md) | movement | On | Concurrent inventory/movement observation only. Touch input, pickup and knockback are not punishable evidence. |
| [gamemodepolicy](gamemodepolicy.md) | policy | Off | Explicit allow-map per game mode; cancels prohibited changes without calling an authorized server action cheating. |
| [gravesaver](gravesaver.md) | management | Off | Optional original death-drop protection by server attribution. No block replacement/item reconstruction; gameplay validation required. |
| [chunkborders](chunkborders.md) | management | Off | Player opt-in particle display when enabled by server policy. |
| [lockdown](lockdown.md) | policy | Off | Restricts new joins; current players retained unless the operator explicitly requests kick. |
| [landclaim](landclaim.md) | policy | Off | Owner/trust controls, overlap buffer and five-claim cap; player changes, explosions, flow and conservative piston protection. Hopper limitations remain. |
