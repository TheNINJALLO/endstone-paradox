Paradox 2.0.1 is the stable native C++ release for Endstone 0.11.11 and BDS 1.26.51.1 / protocol 2193, with Windows x86-64 and Linux x86-64 packages.

Upgrade from the 2.0.0 preview: connected-client testing exposed a command authorization bug. Endstone wraps command senders; the preview could mistake a wrapped player for the console. This release uses the supported `asPlayer()` / `asConsole()` accessors and denies unrecognized senders. Ordinary players cannot change enforcement settings, while explicitly authorized staff can. Player-only commands now work through the same wrapper.

- Initializes connection activity and detection grace periods before the join callback, preventing premature AFK notices and enforcement during spawn.
- Uses supported actor accessors for combat and knockback events, with null checks for absent damage sources.
- Retains the preview's C++ hooks, 54-module audit, SQLite migration backup, native forms and authenticated dashboard, based on upstream Visual1mpact Paradox through v6.9.1.
- Keeps movement/aim/pathing heuristics observational and suspends corroborated detection during lag, unloaded terrain and transitions. No automatic bans.
- Adds a reproducible two-client BDS acceptance harness with isolated latency, jitter, loss, outage and server-stall fixtures, plus gameplay and enforcement positive controls.

Validation records and exact scope are in `native/VALIDATION.md`. Release checks include Windows/Linux native regressions, actual BDS integration tests, and scripted connected clients sending real movement, commands, inventory, combat and form packets. Scripted clients do not reproduce every retail controller, touch, vehicle or custom-item interaction, and no finite suite establishes zero false positives.

The supplied stripped Linux binary cannot yield full private DWARF ABI headers; this plugin uses Endstone's supported C++ ABI and existing server hooks. Grave protection, container inspection and hopper/piston coverage have documented API limits. Review `native/MIGRATION.md` and `native/MODULE_AUDIT.md` before deployment.

Migration: stop the server, back up `plugins/paradox`, remove/uninstall the old Paradox Python wheel, and install exactly one native binary. Keep the existing data folder. Do not run the Python and C++ versions together. BDS binaries are not included.
