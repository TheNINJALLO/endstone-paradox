# Install Paradox Native 2.0.1

## Requirements

| Component | Supported target |
| --- | --- |
| Server framework | Endstone 0.11.11 with its normal runtime/bootstrap |
| Minecraft server | BDS 1.26.51.1, protocol 2193 |
| Platform | Windows x86-64 or Linux x86-64 |
| Linux runtime dependency | OpenSSL 3 (`libssl3` / `libssl3t64`) |

Use the supported target even if a newer Endstone or BDS version exists. An unknown runtime disables packet inspection; management features continuing to run does not establish compatibility. Endstone may display the verified server version as `26.51`.

## Installation and upgrade

1. Download your platform's ZIP and matching `.sha256` file from [stable v2.0.1](https://github.com/TheNINJALLO/endstone-paradox/releases/tag/v2.0.1). Review [release notes](release-notes.md). The v2.0.0 preview is superseded because of a command authorization defect.
2. Stop Endstone and back up the world and `plugins/paradox` directory.
3. Remove the old Paradox `.whl` from `plugins/`, or uninstall `endstone-paradox` from the Python environment used by Endstone if it was installed there. Also remove any previous native Paradox binary.
4. Extract the ZIP and copy **one** plugin binary from its `plugins/` folder into the server's `plugins/` folder: `endstone_paradox.dll` on Windows or `endstone_paradox.so` on Linux. Retain the package's notices and validation files for reference.
5. Keep `plugins/paradox/config.toml` and `plugins/paradox/paradox.db`. The native store creates the consistent migration backup `paradox.db.pre-native.bak`. Read [migration and rollback](migration.md) before changing existing policies.
6. Start Endstone. Confirm `Paradox 2.0.1 native enabled; 54 modules` and no unsupported-protocol warning. Run `ac-about` and `ac-debug-db` from the console.
7. Have the intended administrator join, then run `ac-setclearance "Player Name" 4` from the console. This targets an online player. Review [permission defaults](security.md).

The download contains a plugin, documentation and notices; it does not contain Minecraft server binaries. Do not install the ZIP itself as a Python plugin.

## Check the download

On Linux, from the directory containing the ZIP and checksum:

```sh
sha256sum -c paradox-2.0.1-linux-x86_64.zip.sha256
```

On Windows, compare this value with the provided checksum file:

```powershell
Get-FileHash ./paradox-2.0.1-windows-x86_64.zip -Algorithm SHA256
```

## First session

Use `ac-mode logonly` from the console while checking your own clients and custom mechanics. The default for a new installation is `soft`; a migrated mode is retained. Check `/ac-ping` for a player's detection readiness and `/ac-tps` for server health. Read the [enforcement guide](violation-engine.md) before selecting hard mode.

Enable optional features deliberately using `/ac-modstate <module> on`. Open `/ac-gui` for native forms. The dashboard defaults to `http://127.0.0.1:8080`; its token is in `plugins/paradox/web-token.txt`. See [web setup](webui.md) for remote access.
