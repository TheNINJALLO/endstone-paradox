# Module and upstream audit

Reviewed local Python 1.9.4 (9f500b8), the previous V6 sync on 2026-05-09 (52638ae), and Visual1mpact Paradox v6.9.1 at 568d79b0b225ec1413bc8fa32993bc92591957d8. This is an Endstone-native adaptation, not a claim that the Script API and Endstone expose identical capabilities.

## Upstream changes carried forward

- Offline allow/whitelisting based on stored authenticated identifiers.
- World-border policy, accurate home coordinates and explicit staff clearance.
- PvP consolidation/cooldowns and lockdown that preserves current players.
- Hotbar/input validation, inventory movement review and live inventory deltas/NBT hashing.
- Game-mode policy, chunk borders, land claims and an adapted optional grave safeguard.
- Persistent local history, bounded asynchronous database writes and retained global ban sync state.

Sources: [upstream tree](https://github.com/Visual1mpact/Paradox_AntiCheat/tree/568d79b0b225ec1413bc8fa32993bc92591957d8/penrose), [upstream history](https://github.com/Visual1mpact/Paradox_AntiCheat/commits/master/), and the pinned local reference manifest. Script API-only gameplay extras are not added merely to emulate an unrelated API surface.

## All registered modules

Every observational finding is centrally prevented from escalating, even under hard mode. Health gates and evidence reset tests apply across the detector groups. Policy/utility behavior is separate from an accusation of cheating. Defaults are for a new installation; persisted settings take precedence.

| Module | Default | Native behavior and false-positive decision |
| --- | --- | --- |
| fly | On | Speed/hover observations only; movement/terrain/effect recovery gate. |
| noclip | On | Stone/bedrock overlap observation only; no unloaded-chunk collision verdict. |
| waterwalk | On | Liquid-surface observation only; swimming and effects suspend movement analysis. |
| stephack | On | Vertical-step observation only; slabs, moving blocks and reconciliation cannot prove cheating. |
| timer | On | Three healthy five-second windows of accelerated client time; gaps, bursts, duplicate/reordered ticks reset evidence. Slow input is never flagged. |
| blink | On | Position-discontinuity observation only; teleports, joins and chunk availability reset history. |
| killaura | On | Behind-view hit observation only; interpolation/input devices are not proof. |
| reach | On | Four excessive melee hits beyond conservative distance plus RTT/speed allowance. Attacker and target must be healthy; indirect/projectile/thorns damage, non-player target geometry and extended/unknown weapons are excluded. |
| autoclicker | On | High attack-rate observation only, never a click-cadence ban. |
| antikb | On | Server knockback displacement review only; collision/resistance can explain small movement. |
| criticals | On | Airborne attack observation only; jump apex/effects are not punished. |
| wallhit | On | Bounded loaded-terrain line-of-sight review, limited to known full solid blocks. Observation only. |
| triggerbot | On | Regular attack cadence observation only; controller/held-input behavior is not proof. |
| vision | On | Shares the conservative line-of-sight review. Observation only. |
| scaffold | On | Neighbor support review for block placement. Observation only; custom placement tools are legitimate. |
| xray | On | Ore-ratio review only; veins, exposed ore and custom worlds are not punished. |
| gamemode | On | Compatibility setting: server-authorized mode changes reset movement history and are accepted. Explicit restrictions use gamemodepolicy. |
| namespoof | On | Duplicate online display-name review; identities remain UUID/XUID based. |
| selfinfliction | On | Self-attributed direct melee review only. Reflected/indirect damage is excluded. |
| skinguard | On | Decoded image consistency review only; no bans for transparency, persona or marketplace geometry. |
| illegalitems | On | Overstack review only; custom plugin items are not destroyed. |
| afk | On | Monotonic inactivity tracking; default tips only. Optional configured kick requires healthy connection; legacy timeout is preserved. |
| worldborder | On | Explicit circular boundary policy permits movement back inward when already outside; legacy center fields preserved. |
| lagclear | On | Scheduled administrative cleanup with warning; named/unlimited/protected drops excluded. New installs require explicit removal configuration. |
| pvp | On | Global/personal policy includes projectile attribution, ten-second toggle cooldown, fifteen-second combat interval. Disconnect never bans. |
| ratelimit | Off | Traffic observation only; BDS transport limits remain authoritative. Lag recovery prevents burst punishment. |
| packetmonitor | Off | Traffic counts and review evidence; no packet-size/count auto-ban. |
| containersee | Off | Staff view of looked-at player inventory and container identification through the public API. No raw block-container NBT access. |
| antidupe | Off | Inventory delta/NBT-hash audit. No snapshot rollback, item purge or automatic duplication accusation. |
| crashdrop | Off | Negative server item quantity may cancel a drop. No huge-stack or custom-NBT ban heuristic. |
| invsync | Off | Current inventory deltas and complete item-NBT hashes, including shulkers. Never compares an old snapshot as proof for removing items. |
| discord | On | Bounded asynchronous HTTPS webhook for non-observational findings; configured destination required. |
| chatprotection | On | Rolling one-second chat/command windows, duplicate-message control and legacy mutes. Rate control pauses during recovery; no anti-cheat escalation. |
| antigrief | On | High block-action rate review only; enchantments and building tools do not trigger automatic punishment. |
| evidencereplay | On | Bounded player position/ping/health ring; latest replay stored separately from 100-entry history and 50-entry recent list. |
| adaptivecheck | Off | Records connection baselines. It never lowers enforcement thresholds from lagging samples or untrusted crowd data. |
| botdetection | Off | Explicit configured honeypot interaction observation only; no automatic bot ban. |
| reportsystem | Off | Player reports with cooldown; reports are evidence for staff, never automatic punishments. |
| fingerprint | Off | Salted device hash for review. Shared devices and families are not banned; raw device IDs are not persisted. |
| aimbotmonitor | On | View-change observation only; mouse/controller snaps are not proof of aiming assistance. |
| anticrash | On | Typed protocol-2193 decoding with byte, element and depth budgets. Known malformed inspected packets may cancel; budget excess is fail-open, never a ban. |
| autototem | On | Rapid totem inventory-change review only; no punishment for pickup, lag or custom inventory tools. |
| containerlock | Off | Owner locks and legacy migration; adjacent chests protected; explosions/flows/piston envelope handled. Hopper API limitation documented. |
| deathcoords | On | Fractional death coordinates and dimension are persisted and shown. |
| dimensionlock | Off | Explicit cross-dimension teleport/portal restriction; transitions always reset detection. |
| pathingmonitor | On | Retained setting; robotic-pathing punishment removed. Straight movement and constant yaw are normal. |
| hotbarcheck | On | Slot 0 through 8; validates selection only when should_select_slot is true. Invalid selection cancels without ban. |
| invalidmovementvector | On | Non-finite and out-of-range input axes can cancel; independent diagonal axes of 1,1 are accepted. |
| inventorymovement | On | Concurrent inventory/movement observation only. Touch input, pickup and knockback are not punishable evidence. |
| gamemodepolicy | Off | Explicit allow-map per game mode; cancels prohibited changes without calling an authorized server action cheating. |
| gravesaver | Off | Optional original death-drop protection by server attribution. No block replacement/item reconstruction; gameplay validation required. |
| chunkborders | Off | Player opt-in particle display when enabled by server policy. |
| lockdown | Off | Restricts new joins; current players retained unless the operator explicitly requests kick. |
| landclaim | Off | Owner/trust controls, overlap buffer and five-claim cap; player changes, explosions, flow and conservative piston protection. Hopper limitations remain. |

## Verification boundaries

Core regression tests exercise healthy and lagging movement, target lag, teleport resets, packet bursts, client clock acceleration, independent enforcement histories, all-module observational non-escalation, real packet layouts, truncation/random malformed inputs and SQLite restart/migration. Runtime smoke tests exercise both native loaders, commands, HTTP authorization, queue dispatch and clean shutdown. They do not simulate all 54 modules inside a connected live client. Physical mechanics, grave attribution, custom items and third-party plugin interactions still require gameplay acceptance testing.
