"""Qualify a fresh native build against the pinned official disposable BDS."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import endstone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("linux", "windows"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    profile = json.loads((root / "native/references.lock.json").read_text())
    assert endstone.__version__ == profile["endstone"]
    scratch = root / "scratch"
    scratch.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="runtime-qualification-", dir=scratch))
    server = output / "server"
    server.mkdir()
    archive = output / "server.zip"
    target = "win" if args.platform == "windows" else "linux"
    url = f"https://www.minecraft.net/bedrockdedicatedserver/bin-{target}/bedrock-server-{profile['server']}.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as source, archive.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)
    with archive.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == profile["archives"][args.platform]["sha256"]
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            assert (server / name).resolve().is_relative_to(server.resolve())
        package.extractall(server)
    executable = server / ("bedrock_server.exe" if args.platform == "windows" else "bedrock_server")
    with executable.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == profile["archives"][args.platform]["binary_sha256"]
    if args.platform == "linux":
        executable.chmod(0o755)
    library = root / "build" / args.platform / ("endstone_paradox.dll" if args.platform == "windows" else "endstone_paradox.so")
    report = output / "report"
    subprocess.run([sys.executable, str(root / "native/tools/smoke-server.py"), str(server), str(library), str(report)], check=True, timeout=240)
    evidence = json.loads((report / f"{args.platform}.json").read_text())
    evidence.update(endstone=profile["endstone"], bedrock=profile["server"], protocol=profile["protocol"],
                    binary_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
                    scope="Disposable native server startup, authenticated commands, persistence and shutdown; no retail client attached")
    destination = root / "dist/native" / f"paradox-runtime-{args.platform}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Qualified native {args.platform} runtime; evidence: {destination}", flush=True)


if __name__ == "__main__":
    main()
