Paradox 2.0.0 is the first native C++ preview for Endstone 0.11.11 and BDS 1.26.51.1 / protocol 2193, with Windows x86-64 and Linux x86-64 packages.

- Replaces the Python plugin runtime with C++ event/packet hooks, SQLite persistence, native forms and an authenticated dashboard.
- Reviews upstream Visual1mpact Paradox through v6.9.1 and adds the native equivalents/adaptations documented in the module audit.
- Removes robotic-pathing punishment and combined heuristic escalation. Lag, jitter, server stalls, packet bursts, unloaded terrain and movement transitions reset evidence. No automatic bans.
- Preserves the client-clock baseline through recovery so a slowly draining input backlog cannot become fresh timer evidence while the client is still catching up.
- Accepts legitimate large subchunk requests and uses pinned, bounded protocol decoders checked against an actual dump of the supplied BDS build.
- Preserves existing data with a consistent SQLite migration backup; archives the old Python implementation separately.

Validation: Windows/Linux native builds and core regressions pass, plus 17 integration checks per platform against the supplied servers. Tests cover lag recovery, straight-line movement, hotbar boundaries, an 8,192-offset chunk request, malformed input, database restart persistence and web authorization.

This is a **pre-release pending multiplayer gameplay and packet-loss soak testing**. It does not promise zero false positives. The supplied stripped Linux binary cannot yield full private DWARF ABI headers; the plugin uses Endstone's supported C++ ABI and existing server hooks. Grave protection, container inspection and hopper/piston coverage have documented API limits. Review `native/MIGRATION.md`, `native/MODULE_AUDIT.md` and `native/VALIDATION.md` before deployment.

Migration: stop the server, back up `plugins/paradox`, remove/uninstall the old Paradox Python wheel, and install exactly one native binary. Keep the existing data folder. Do not run the Python and C++ versions together. BDS binaries are not included.
