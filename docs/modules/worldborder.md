# worldborder

Paradox Native 2.0.1 | **Management** | New-install default: **On**

## Native behavior

Explicit circular boundary policy permits movement back inward when already outside; legacy center fields preserved.

## Controls

Use `/ac-modstate worldborder on` or `/ac-modstate worldborder off`. The generic module handler requires clearance 3 or `paradox.modules`, plus clearance 4 or `paradox.settings` to change state. Operators have these permissions by default. Changes persist to SQLite and override TOML defaults. For utility commands and special cases, see [module controls](../commands/toggles.md) and [player utilities](../commands/utility.md).

## Evidence and limits

Observations never escalate into punishment, including in hard mode. Administrative policies are separate from cheating findings. Read the [lag and enforcement guide](../violation-engine.md) and [full module audit](../module-audit.md) before changing policy. The [validation record](../validation.md) distinguishes automated coverage from gameplay still needing local acceptance.

[All modules](overview.md)
