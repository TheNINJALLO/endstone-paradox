# Evidence and integration boundaries

The native release does not import crowd-sourced thresholds or automatically tune enforcement from remote behavior reports. Historical Python intelligence-network and EMA sensitivity descriptions are not native features.

| Native feature | What it does |
| --- | --- |
| [Adaptive check](modules/adaptivecheck.md) | Records connection baselines; does not tighten thresholds from lag or crowd data |
| [Fingerprint](modules/fingerprint.md) | Optional salted device hash for staff review; raw device IDs are not persisted |
| [Reports](modules/reportsystem.md) | Optional player reports with cooldown; no automatic punishment |
| [Evidence replay](modules/evidencereplay.md) | Bounded position/ping/health context for staff review |
| [Global database](global-database.md) | Explicit optional HTTPS synchronization and corroborated reports |

Shared devices, family connections, reports and repeated observational findings are not proof of cheating. Review [enforcement](violation-engine.md), [configuration](configuration.md) and [migration](migration.md) before enabling optional integrations.
