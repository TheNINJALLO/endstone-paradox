"""Run only against a disposable extracted BDS server. Overwrites its test configuration."""

import json, os, queue, re, shutil, sqlite3, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path

server, plugin, output = map(Path, sys.argv[1:4])
server = server.resolve()
output = output.resolve()
output.mkdir(parents=True, exist_ok=True)
if "scratch" not in server.parts and not str(server).startswith("/runtime/"):
    raise SystemExit("Refusing to overwrite a non-disposable server directory")
(server / "plugins" / "paradox").mkdir(parents=True, exist_ok=True)
shutil.copy2(plugin, server / "plugins" / plugin.name)
(server / "plugins" / "paradox" / "config.toml").write_text(
    '[web_ui]\nenabled=true\nhost="127.0.0.1"\nport=39303\n[global_database]\nenabled=false\n[modules.lagclear]\nenabled=false\n'
)
(server / "server.properties").write_text(
    "server-name=Paradox isolated native test\nserver-port=39301\nserver-portv6=39302\nallow-list=false\nonline-mode=false\nlevel-name=paradox-native-test\nview-distance=4\ntick-distance=4\nemit-server-telemetry=false\nenable-lan-visibility=false\nclient-side-chunk-generation-enabled=false\ntransport=nethernet\n"
)
(server / "endstone.toml").write_text("[settings]\n")
isolation = output / "isolation"
isolation.mkdir(exist_ok=True)
(isolation / "sitecustomize.py").write_text(
    'import os,sys\nsys.path[:]=[p for p in sys.path if "site-packages" not in p.lower() or p.lower().startswith(os.environ["PARADOX_SMOKE_PREFIX"].lower())]\n'
)


def environment(boot):
    env = boot._endstone_runtime_env
    env["PYTHONPATH"] = str(isolation) + os.pathsep + env["PYTHONPATH"]
    env["PARADOX_SMOKE_PREFIX"] = sys.prefix
    env["PYTHONNOUSERSITE"] = "1"
    return env


if os.name == "nt":
    from endstone.cli.windows import WindowsBootstrap, PopenWithDll

    boot = WindowsBootstrap(str(server), True, "", False)
    process = PopenWithDll(
        [str(boot.executable_path)],
        cwd=server,
        env=environment(boot),
        dll_names=str(boot._endstone_runtime_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
else:
    from endstone.cli.linux import LinuxBootstrap

    boot = LinuxBootstrap(str(server), True, "", False)
    boot.executable_path.chmod(0o755)
    process = subprocess.Popen(
        [str(boot.executable_path)],
        cwd=server,
        env=environment(boot),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
lines = []
messages = queue.Queue()


def reader():
    for line in process.stdout:
        lines.append(line)
        messages.put(line)


threading.Thread(target=reader, daemon=True).start()
checks = {}


def command(text):
    process.stdin.write(text + "\n")
    process.stdin.flush()


def request(path, token=None, data=None):
    headers = {} if token is None else {"Authorization": "Bearer " + token}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:39303" + path, headers=headers, data=data
            ),
            timeout=5,
        ) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


try:
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "Server exited before startup: " + str(process.returncode)
            )
        try:
            line = messages.get(timeout=1)
        except queue.Empty:
            continue
        if "Server started" in line:
            break
    else:
        raise RuntimeError("Server startup timed out")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if any("native enabled" in l for l in lines):
            try:
                token = (server / "plugins/paradox/web-token.txt").read_text().strip()
                if "version" in json.loads(request("/api/status", token)[1]):
                    break
            except (OSError, ValueError):
                pass
        time.sleep(0.5)
    checks["enabled"] = any("native enabled" in l for l in lines)
    if not checks["enabled"]:
        raise RuntimeError("Native plugin did not enable")
    for c in [
        "plugins",
        "ac-about",
        "ac-mode logonly",
        "ac-modstate pathingmonitor on",
        "ac-debug-db",
    ]:
        command(c)
    token = (server / "plugins/paradox/web-token.txt").read_text().strip()
    checks["anonymous_status_rejected"] = request("/api/status")[0] == 401
    checks["invalid_token_rejected"] = request("/api/status", "invalid")[0] == 401
    status, body = request("/api/status", token)
    data = json.loads(body)
    expected_version = re.search(r"project\(paradox VERSION ([\d.]+)", (Path(__file__).resolve().parents[2] / "CMakeLists.txt").read_text())[1]
    checks["authenticated_status"] = status == 200 and data["version"] == expected_version
    checks["protocol_supported"] = data["protocol_supported"]
    checks["all_modules_registered"] = len(data["modules"]) == 54
    checks["malformed_command_rejected"] = (
        request("/api/command", token, {"command": []})[0] == 400
    )
    checks["multiline_command_rejected"] = (
        request("/api/command", token, {"command": "ac-about\nstop"})[0] == 400
    )
    checks["oversized_body_rejected"] = (
        request("/api/command", token, {"command": "ac-about " + "x" * 9000})[0] == 413
    )
    checks["arbitrary_console_rejected"] = request(
        "/api/command", token, {"command": "stop"}
    )[0] in (400, 403)
    checks["native_command_queued"] = request(
        "/api/command", token, {"command": "ac-modstate pathingmonitor off"}
    )[0] in (200, 202)
    time.sleep(3)
    checks["native_command_executed"] = (
        json.loads(request("/api/status", token)[1])["modules"]["pathingmonitor"][
            "enabled"
        ]
        is False
    )
    command("ac-debug-db")
    time.sleep(1)
finally:
    if process.poll() is None:
        command("stop")
        try:
            process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            checks["graceful_stop"] = False
    time.sleep(0.5)
    (output / ("windows" if os.name == "nt" else "linux")).with_suffix(
        ".log"
    ).write_text("".join(lines), encoding="utf-8")
    checks["exit_zero"] = process.returncode == 0
    checks["only_native_plugin"] = any("Plugins (1): paradox" in l for l in lines)
    (output / ("windows" if os.name == "nt" else "linux")).with_suffix(
        ".json"
    ).write_text(json.dumps(checks, indent=2))
with sqlite3.connect(server / "plugins/paradox/paradox.db") as db:
    checks["mode_persisted"] = (
        json.loads(
            db.execute(
                "SELECT value FROM config WHERE key=?", ("enforcement_mode",)
            ).fetchone()[0]
        )
        == "logonly"
    )
    checks["module_persisted"] = (
        json.loads(
            db.execute(
                "SELECT value FROM modules WHERE key=?", ("pathingmonitor",)
            ).fetchone()[0]
        )["enabled"]
        is False
    )
checks["no_plugin_runtime_errors"] = not any(
    "Paradox tick:" in l
    or "Event inspection suspended:" in l
    or "Paradox startup failed:" in l
    for l in lines
)
(output / ("windows" if os.name == "nt" else "linux")).with_suffix(".json").write_text(
    json.dumps(checks, indent=2)
)
print(json.dumps(checks, indent=2), flush=True)
if not checks or not all(checks.values()):
    raise SystemExit("Native server smoke test failed")
