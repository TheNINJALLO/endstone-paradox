"""Hold an isolated BDS test server; accept console commands from control.ndjson.

This runner is for scripted acceptance tests, not production. It overwrites
the disposable server configuration and uses a separate acceptance world.
"""

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

p = argparse.ArgumentParser()
p.add_argument("server", type=Path)
p.add_argument("plugin", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--seconds", type=int, default=1800)
p.add_argument("--transport", choices=("nethernet", "raknet"), default="nethernet")
args = p.parse_args()
server, output = args.server.resolve(), args.output.resolve()
if "scratch" not in server.parts and not str(server).startswith("/runtime/"):
    raise SystemExit("Only disposable scratch or /runtime/ servers are accepted")
output.mkdir(parents=True, exist_ok=True)
data = server / "plugins/paradox"
data.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.plugin, server / "plugins" / args.plugin.name)
(data / "config.toml").write_text(
    '[web_ui]\nenabled=true\nhost="127.0.0.1"\nport=39303\n'
    "[global_database]\nenabled=false\n[modules.lagclear]\nenabled=false\n"
    "[modules.discord]\nenabled=false\n[afk]\nkick=false\n"
)
(server / "server.properties").write_text(
    "server-name=Paradox acceptance test\nserver-port=39301\nserver-portv6=39302\n"
    "allow-list=false\nonline-mode=false\nallow-cheats=true\ngamemode=survival\n"
    "difficulty=peaceful\nlevel-name=paradox-acceptance\nview-distance=8\ntick-distance=4\n"
    "emit-server-telemetry=false\nenable-lan-visibility=true\n"
    f"client-side-chunk-generation-enabled=false\ntransport={args.transport}\n"
)
(server / "endstone.toml").write_text("[settings]\n")
isolation = output / "isolation"
isolation.mkdir(exist_ok=True)
(isolation / "sitecustomize.py").write_text(
    'import os,sys\nsys.path[:]=[p for p in sys.path if "site-packages" not in p.lower() '
    'or p.lower().startswith(os.environ["PARADOX_SMOKE_PREFIX"].lower())]\n'
)
if os.name == "nt":
    from endstone.cli.windows import WindowsBootstrap, PopenWithDll

    boot = WindowsBootstrap(str(server), True, "", False)
else:
    from endstone.cli.linux import LinuxBootstrap

    boot = LinuxBootstrap(str(server), True, "", False)
    boot.executable_path.chmod(0o755)
env = boot._endstone_runtime_env
env["PYTHONPATH"] = str(isolation) + os.pathsep + env["PYTHONPATH"]
env["PARADOX_SMOKE_PREFIX"] = sys.prefix
env["PYTHONNOUSERSITE"] = "1"
options = dict(
    cwd=server,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
)
if os.name == "nt":
    proc = PopenWithDll(
        [str(boot.executable_path)],
        dll_names=str(boot._endstone_runtime_path),
        creationflags=subprocess.CREATE_NO_WINDOW,
        **options,
    )
else:
    proc = subprocess.Popen([str(boot.executable_path)], **options)
messages = queue.Queue()
lines = []


def read():
    for line in proc.stdout:
        lines.append(line)
        messages.put(line)


threading.Thread(target=read, daemon=True).start()


def command(text):
    if "\n" in text or "\r" in text:
        raise ValueError("One console command per control record")
    proc.stdin.write(text + "\n")
    proc.stdin.flush()


control = output / "control.ndjson"
control.write_text("")
deadline = time.monotonic() + args.seconds
offset = 0
ready = False
try:
    while time.monotonic() < deadline and proc.poll() is None:
        try:
            line = messages.get(timeout=0.1)
            if "Server started" in line and not ready:
                ready = True
                for cmd in [
                    "ac-mode hard",
                    "ac-modstate pathingmonitor on",
                    "ac-modstate lagclear off",
                    "gamerule doMobSpawning false",
                    "gamerule doDaylightCycle false",
                    "gamerule sendCommandFeedback true",
                    "setworldspawn 0 301 0",
                    "tickingarea remove paradox_test",
                    "tickingarea add -64 0 -64 64 0 64 paradox_test",
                ]:
                    command(cmd)
                time.sleep(3)
                command("fill -64 300 -64 64 300 64 stone")
                (output / "ready.json").write_text(
                    json.dumps({"pid": proc.pid, "port": 39301})
                )
                print("Isolated acceptance server ready", flush=True)
        except queue.Empty:
            pass
        with control.open() as f:
            f.seek(offset)
            for line in f:
                if line.strip():
                    command(json.loads(line)["command"])
            offset = f.tell()
        (output / "server.log").write_text("".join(lines), encoding="utf-8")
        if (output / "stop").exists():
            break
finally:
    if proc.poll() is None:
        command("stop")
        try:
            proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    (output / "server.log").write_text("".join(lines), encoding="utf-8")
    (output / "exit.json").write_text(json.dumps({"exit_code": proc.returncode}))
    print("Acceptance server stopped:", proc.returncode, flush=True)
if proc.returncode != 0 or not ready:
    raise SystemExit(1)
