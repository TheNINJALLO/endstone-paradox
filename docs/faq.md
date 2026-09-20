# Frequently asked questions

## Which file do I install?

Extract the [v2.0.1 platform ZIP](https://github.com/TheNINJALLO/endstone-paradox/releases/tag/v2.0.1) and install exactly one `endstone_paradox.dll` or `endstone_paradox.so` into `plugins/`. Remove the old Paradox wheel. [Installation guide](gettingstarted.md).

## Does C++ mean Endstone no longer needs Python?

The Paradox plugin is native. Endstone still uses its normal bootstrap/runtime. The archived Python Paradox package must not also be loaded.

## Will this punish straight movement or lag?

Robotic pathing is retired as a cheating verdict. Relevant checks suspend during lag, unloaded terrain, transitions and recovery. Review-only heuristics never escalate into punishment. Scripted lag acceptance passed, but that cannot establish zero false positives for every retail client or custom mechanic. [Enforcement](violation-engine.md) and [validation](validation.md).

## Why does detection say it is suspended?

Use `/ac-ping` to see the reason and `/ac-tps` to check server load. Unknown/rounded-zero ping, packet recovery, effects or a recent teleport can keep the health gate closed. Timer clock deficits deliberately favor avoiding lag punishment over detecting every acceleration.

## Why do old sensitivity commands fail?

The native engine does not use the Python 1-10 sensitivity scale. Use `/ac-modstate <module> on|off` and `/ac-mode soft|hard|logonly`; read [module behavior](modules/overview.md).

## Why did my TOML module change not take effect?

Persisted module state in SQLite wins over TOML defaults. Use the runtime module command, GUI or dashboard. See [configuration precedence](configuration.md).

## How do I become an administrator?

Join the server and have its console run `ac-setclearance "Player Name" 4`. The old first-run password form does not exist in the native release. Operators receive staff permissions by default. [Security guide](security.md).

## Why can I not access the dashboard from another machine?

New installs bind to localhost. Use an SSH tunnel or HTTPS reverse proxy and the generated bearer token. Existing host/port configuration is preserved. [Web setup](webui.md).

## Are graves, containers and land claims complete replacements for protection plugins?

Read the [API limits](migration.md): no public block-container inventory API, no hopper-transfer callback and no complete piston moved-block list are available in the targeted API. Grave safeguarding is optional and requires gameplay testing; it is not guaranteed item reconstruction.

## Can I stay on the 2.0.0 preview?

Upgrade to 2.0.1. Live acceptance found a command-sender authorization defect and premature AFK initialization in that preview. Both are fixed in the stable release. [Release notes](release-notes.md).

## How do I report a problem?

Open a [repository issue](https://github.com/TheNINJALLO/endstone-paradox/issues) with plugin/Endstone/BDS versions, platform, reproduction steps, module/mode, relevant ping/TPS and sanitized evidence. Include whether it reproduces with other plugins disabled in a disposable server. Never attach the web token, webhook URL, API key or private database.
