"""Repackage qualified CI binaries with current documentation, preserving binary bytes."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
for platform, suffix in (("linux", "so"), ("windows", "dll")):
    source = root / "ci-artifacts" / platform
    evidence = json.loads((source / f"paradox-runtime-{platform}.json").read_text())
    assert evidence["endstone"] == "0.11.16" and evidence["bedrock"] == "1.26.65.1" and evidence["protocol"] == 2225
    checks = [value for value in evidence.values() if isinstance(value, bool)]
    assert len(checks) >= 15 and all(checks)
    package = next(source.glob(f"paradox-2.0.4-{platform}-x86_64.zip"))
    with zipfile.ZipFile(package) as archive:
        binary = archive.read(f"plugins/endstone_paradox.{suffix}")
    assert hashlib.sha256(binary).hexdigest() == evidence["binary_sha256"]
    record = root / "native/validation" / f"endstone-0.11.16-{platform}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(evidence, indent=2) + "\n")
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / f"endstone_paradox.{suffix}"
        path.write_bytes(binary)
        subprocess.run([sys.executable, str(root / "native/tools/package.py"), str(path), "--platform", platform], cwd=root, check=True)
    shutil.copy2(source / f"paradox-runtime-{platform}.json", root / "dist/native" / f"paradox-runtime-{platform}.json")
