# Release status and remaining validation

**2.0.1 is the stable native C++ release.** It includes the 54-module audit, Windows/Linux packages, SQLite migration, upstream review through Visual1mpact v6.9.1, supported Endstone hooks, native forms and the authenticated dashboard. It supersedes the v2.0.0 preview.

Completed automated coverage includes core regressions, actual BDS loading/integration and scripted connected-client gameplay/network checks on Windows and Linux. The [validation record](validation.md) and release `release-validation.json` identify the scope and artifact provenance.

Further acceptance work remains for retail controller/touch clients, portals, elytra/riptide/vehicles, slime/honey/pistons, custom items, optional graves and other plugin combinations. These are validation boundaries, not promises of a delivery date or claims that every module has been exercised by a retail client.

Future BDS/protocol targets require fresh ABI/schema review and acceptance runs. Changes to container/hopper/piston coverage depend on supported server APIs. Crowd-sourced automatic enforcement tuning and the archived Python UI are not native release commitments.

See [release notes](release-notes.md), [module audit](module-audit.md) and [migration limits](migration.md) before deployment.
