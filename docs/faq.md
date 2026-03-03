# FAQ

## General

### How do I install the plugin?
Place the `.whl` file in your Endstone server's `plugins/` directory and restart. See [Getting Started](gettingstarted.md).

### What version of Endstone is required?
Paradox is built against the latest Endstone API. Check `pyproject.toml` for the exact version requirement.

### Does it work on Realms?
No — Paradox requires an **Endstone server** (similar to BDS with Endstone installed). It does not work on Realms.

## Modules

### Why are some modules OFF by default?
The anti-dupe modules (`antidupe`, `crashdrop`, `invsync`), rate limiter, packet monitor, and container see are OFF by default because they need per-server tuning. Enable them gradually and adjust sensitivity.

### How do I adjust sensitivity?
```
/ac-modules <module> sensitivity <1-10>
```
Or use the Web UI's Modules page.

### Will the anti-dupe module break hopper clocks?
No! The hopper cluster monitoring tracks **total item counts** — hopper clocks move items back and forth without increasing the total, so they're completely safe.

### What's the difference between the Anti-Dupe module and Crash-Drop?
- **Anti-Dupe** detects item multiplication (bundles in containers, piston dupes, packet exploits)
- **Crash-Drop** prevents items from being duplicated when a player crashes/disconnects

## Security

### I forgot my admin password. What do I do?
Delete the `admin_hash` entry from `config.toml` and restart the server. Then run `/ac-op` to set a new password.

### Can operators bypass the clearance system?
Server operators are not automatically given clearance. They must authenticate via `/ac-op` like everyone else.

## Web UI

### How do I change the web UI port?
Edit `config.toml`:
```toml
[web_ui]
port = 8080
```

### Is the web UI secure?
The web UI uses a secret key for authentication. For production use, we recommend running it behind a reverse proxy with HTTPS.

## Troubleshooting

### Module X shows "disabled" but I toggled it on
Module states are stored in the database. Try:
```
/ac-debug-db modules
```
to verify the stored state. If there's a mismatch, toggle it off and on again.

### The web UI won't start
Check that port 8005 is not in use by another process. Also verify Flask is installed:
```
pip install flask
```
