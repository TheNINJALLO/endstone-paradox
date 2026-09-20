# Validation record

Target review date: 2026-09-19. The repository manifest pins every reference used below.

## Supplied BDS builds

Both archives and their executables were SHA-256 checked against the official bedrock-server-data release/1.26.51 metadata. Expected hashes are recorded in references.lock.json. The Linux executable build ID is ea299d3d03fca9827d3e71cf4e503ede30ba9805. Both servers report commit 0559ac59aa24e42d30e238bc55cdb306232a6507; Linux build 51061372 and Windows build 51061361.

Endstone reports this version as **26.51**, although BDS reports **1.26.51.1**. The runtime gate recognizes that verified Endstone format and requires protocol 2193.

## How the requested repositories were used

| Reference | Use |
| --- | --- |
| Endstone | Pinned native plugin headers, CMake plugin target, scheduler, ItemStack/NBT APIs and hooked packet/game events; examined hook implementations to confirm payloads exclude the packet header. |
| bedrock-protocol | Compiled typed protocol-2193 codecs. Added explicit string-allocation, element-count and recursive-depth inspection budgets. |
| protocol-docs | Independent reflected wire schema reference. Compared relevant JSON against actual BDS reflection output. |
| protocol-dumper | Built with the supplied Linux BDS archive and exact supported version; ran its injected reflection dumper against that executable. |
| dwarf2cpp | Reviewed its DWARF requirements. The supplied Linux executable has a debug-link section but no DWARF type information. Complete private ABI headers cannot be generated from this stripped archive. No fabricated headers/offsets were used. |
| bedrock-server-data | Matched the supplied archive and binary checksums to official version metadata. |
| remote-dev | Used its LLVM20/libc++ toolchain requirements for the isolated native build environment; no SSH service or developer keys were needed. |
| Visual1mpact Paradox | Compared the prior local V6 sync with upstream v6.9.1; see MODULE_AUDIT.md for native mappings and deliberate adaptations. |

## Actual protocol dump

The dumper completed against BDS 1.26.51.1 and shut down cleanly. It visited 987 reflected types and wrote **729 JSON schemas: 231 packets, 160 enums and 338 types**; 258 reflection types were skipped by the dumper. The six inspected packet schemas exactly matched the pinned protocol-docs JSON: PlayerAuthInput (144), PlayerHotbar (48), SubChunkRequest (175), MobEffect (28), SetActorMotion (40) and MovePlayer (19).

[Protocol comparison hashes](validation/protocol-comparison.json) retain the comparison result. Independent byte fixtures cover hotbar field order and MobEffect's trailing Ambient field. Generated-code round trips are additional checks, not the sole source of wire-layout validation.

## Automated regression coverage

The deterministic native executable covers:

- High/unknown/non-finite ping, jitter, low TPS, slow ticks, unloaded terrain, exemptions and recovery.
- Straight movement without robotic-pathing findings; diagonal input; yaw wrapping.
- Healthy timer/reach positive controls, slow-client negative controls, lagging target protection and teleport resets.
- A 20-second input backlog draining at 30 packets/second for 40 seconds, followed by normal input. Timer evidence stays suspended until the retained session clock catches up; a recovery reset cannot discard that clock anchor.
- Separate evidence by player and module; observations from all 54 registered modules never escalate under hard mode.
- Valid hotbar boundaries and unused selection fields; valid 8,192-offset subchunk requests larger than the former 16 KiB cutoff.
- Every truncated prefix of an auth-input fixture and 3,000 deterministic malformed-input samples; bounded decoding with no partial input delivered.
- SQLite legacy-schema migration, fractional coordinates, backup, 1,000 asynchronous writes, shutdown/reopen persistence and deletion.

CTest runs one native executable containing these scenarios and looped assertions. Its assertion count is not a count of distinct test cases.

The timer guard intentionally favors missed detections over punishing delayed inputs. A client whose clock stays behind after a pause may remain exempt from timer enforcement for the session; other checks retain their normal health gates. Inputs buffered before the first observed packet cannot be distinguished perfectly from an accelerated clock. Use `ac-mode logonly` for initial multiplayer acceptance testing; the default remains `soft` and existing persisted modes are retained.

## Real server smoke tests

Native Windows DLL and Linux shared-library smoke tests use the supplied BDS builds with Endstone 0.11.11. They verify native load/enable, supported protocol gating, console commands, unauthenticated/invalid-token rejection, authenticated dashboard snapshots, arbitrary-console-command rejection, main-thread queued command execution, a single active plugin and graceful stop. JSON results are retained under validation/ after final verification.

The Windows test environment filters global Python site packages to ensure only the native Paradox plugin is loaded. Linux runs in an isolated Docker server directory. Paradox global reporting and Discord destinations are disabled. These are startup/integration tests, not multiplayer gameplay tests.

## Connected-client acceptance

The 2.0.1 acceptance harness connects two scripted protocol-2193 clients to each actual Windows/Linux BDS runtime. It completes both initial spawn and the loading-screen-finished handshake. Without the latter, BDS protects the client during loading; a join message alone is not proof of a functioning gameplay client. The client follows server corrections and sends real movement, inventory, command, attack and form-response packets.

The suite requires active detection during ordinary walking and after recovery. During legitimate phases, both players must remain connected, no new enforcement is permitted, and robotic-pathing findings are forbidden. The deliberately invalid-input phases have separate positive assertions so disabling every detector cannot make the suite pass.

Coverage:

- Join/AFK initialization; ordinary-player denial of staff settings; explicitly granted staff clearance; fractional home storage and actual return teleport.
- Ground walking and valid hotbar slots 0 through 8.
- Client network delay of 300 ms with 100 ms normally distributed jitter and 3% packet loss, followed by recovery to 30 ms. Linux `netem` affects only each dedicated client container.
- A three-second total packet outage with buffered recovery on both server platforms.
- A two-second forced stall of the isolated Linux BDS process, followed by recovery. The Windows process is not forcibly suspended.
- Teleport and speed-effect grace periods and recovery.
- Real close-range player melee, verified by server health updates; refusal to disable PvP during combat; delivered and cancelled native GUI forms.
- Cancellation of hotbar slot 9 without kicking the player, and corroborated timer enforcement against a sustained 30 Hz input clock. The Linux run used 30 packets/second; the Windows fixture separates the accelerated clock from steady 20-packet/second delivery because BDS tick batching can otherwise activate burst protection. That protection intentionally defers timer enforcement during bursts.

Two actual native bugs were found by these tests and corrected: premature AFK state before PlayerJoin, and wrapped CommandSender instances being treated as console senders. The latter permitted unauthorized settings changes in the 2.0.0 preview. Supported `asPlayer()` / `asConsole()` accessors now identify the sender, and unrecognized senders are denied. Actor accessors were corrected for combat and knockback as well.

All 72 Linux and 66 Windows connected-client assertions passed for the local 2.0.1 candidates. These are named checks, including per-phase connection and enforcement assertions; they are not 138 distinct gameplay scenarios.

Machine-readable results are retained as `validation/windows-network.json` and `validation/linux-network.json`, with the exact tested local plugin hashes and version. Build and smoke results are separate records. Release artifacts also receive final binary smoke checks; their provenance is attached to the GitHub release as `release-validation.json`. The Go client dependency versions and checksums are committed under `tests/bedrock-client`; reproduction steps are in BUILDING.md.

## Remaining gameplay coverage

These are scripted clients, not connected retail clients. Controller/touch input, portals, elytra/riptide/vehicles, slime/honey/pistons, custom items, graves and combinations with other plugins still need environment-specific gameplay testing. Optional policy limitations are listed in MIGRATION.md. The implementation avoids automatic heuristic bans, but no finite test suite can establish zero false positives in every live environment.
