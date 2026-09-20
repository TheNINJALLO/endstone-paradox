# Native migration and configuration

## Preserved data

The plugin uses the existing `plugins/paradox` directory and SQLite JSON key/value schema. A consistent `.pre-native.bak` is completed under a temporary name before it becomes the migration backup. Writes use transactions, WAL, FULL synchronization, a bounded/coalesced queue and shutdown flush. Persistence failures are reported. Keep an independent backup when upgrading.

Homes, fractional coordinates, dimensions, local bans, clearance, module toggles, ranks, frozen players, allow/whitelists, PvP policy, reports and historical tables remain in the database. Legacy `chestLockDB` keys are read alongside native keys and removed when the owner unlocks or breaks the container. Muted-player configuration is read from the legacy table. Reload starts a fresh detection recovery interval.

Remote name-only bans are not enforced automatically. Offline list additions require a previous joined player's UUID/XUID history; a display name alone is not authenticated identity. Local operator-created legacy name bans are retained. Review old false-positive local bans manually; migration never deletes operator records automatically.

Disabling global synchronization stops future requests; it does not erase existing `global_bans`. Cached XUID-matched ban records still apply at join. Review the retained policy when migrating or disconnecting from a remote service.

## Deliberate behavior changes and limits

- Robotic pathing is retired as a cheating verdict. `pathingmonitor` remains a compatible setting; movement/recovery evidence is available through replays.
- Observational checks cannot accumulate into punishment. Python sensitivity values do not restore the old combined-score escalation.
- Combat disconnects never create bans: a lost connection is not proof of intentional combat logging.
- Inventory synchronization records current deltas and full item-NBT hashes, including shulkers. It never destroys items because they differ from an earlier snapshot. Copies use Endstone ItemStacks to preserve metadata.
- Skin geometry, persona skins, transparency, shared devices and unusual/custom items do not cause automatic kicks.
- `gravesaver` protects attributable original nearby death-drop entities and preserves their ItemStacks. It does not replace blocks with grave chests/signs. It is off by default. Attribution and pickup behavior need gameplay validation; this is not guaranteed item recovery.
- `containersee` displays looked-at player inventory pages and identifies containers. Endstone 0.11.11 does not expose block-container inventory through its public API.
- Container/land policies cover player interactions, block changes, explosions, liquid ingress and a conservative piston envelope. Endstone provides no hopper-transfer callback or complete piston moved-block list. Existing hopper automation and unusual slime/honey structures require server-specific protection/testing.
- Random teleport selects already loaded, supported terrain with headroom and reports failure when none is found.
- Vanish applies invisibility and hides the name tag. It does not remove the player from the player list or suppress all actor packets.
- A compass named `Paradox Menu` opens the native GUI, subject to command authorization.
- Native web authentication uses a generated bearer token. Old web sessions/password forms are not reused. The historical Python UI and optional crowd-sourced auto-tuning are archived; remote thresholds do not change native enforcement.

## New-install configuration

```toml
[web_ui]
enabled = true
host = "127.0.0.1"
port = 8080

[global_database]
enabled = false
api_url = "" # Explicit HTTPS endpoint; no hidden HTTP fallback
api_key = "" # Registration result is persisted locally if omitted
sync_interval = 300

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

Existing module/database values take precedence over defaults. Existing lag-clear configuration retains its prior enabled behavior; new installations require `enabled_removal = true` to permit scheduled removal. Named/protected items and grave items are excluded. Integrations require an explicit destination; validation sends no live Paradox reports.

Use `/ac-modstate <name> on|off` for module names whose short command is also a utility (PvP, chunk borders, land claims). `/ac-evidencereplay on|off` toggles recording; a player argument shows their latest replay. `ac-home` with no arguments uses `default`; `ac-home list` lists locations.

## Rollback

Stop Endstone, remove the native binary, restore the Python package and pre-upgrade data directory. Replace the database while stopped, including removal of stale WAL/SHM files belonging to that replaced database. Keep the current native database separately to preserve newer moderation records.
