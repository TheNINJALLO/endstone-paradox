# hotbarcheck

Paradox Native 2.0.1 | **Validation** | New-install default: **On**

## Native behavior

Slot 0 through 8; validates selection only when should_select_slot is true. Invalid selection cancels without ban.

## Controls

Use `/ac-modstate hotbarcheck on` or `/ac-modstate hotbarcheck off`. The generic module handler requires clearance 3 or `paradox.modules`, plus clearance 4 or `paradox.settings` to change state. Operators have these permissions by default. Changes persist to SQLite and override TOML defaults. For utility commands and special cases, see [module controls](../commands/toggles.md) and [player utilities](../commands/utility.md).

## Evidence and limits

Observations never escalate into punishment, including in hard mode. Administrative policies are separate from cheating findings. Read the [lag and enforcement guide](../violation-engine.md) and [full module audit](../module-audit.md) before changing policy. The [validation record](../validation.md) distinguishes automated coverage from gameplay still needing local acceptance.

[All modules](overview.md)
