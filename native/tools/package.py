"""Package a tested native binary and documentation; never include server files/secrets."""

import argparse
import hashlib
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

parser = argparse.ArgumentParser()
parser.add_argument("binary", type=Path)
parser.add_argument("--platform", required=True, choices=("linux", "windows"))
parser.add_argument("--output", type=Path, default=Path("dist/native"))
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
version = re.search(
    r"project\(paradox VERSION ([\d.]+)", (root / "CMakeLists.txt").read_text()
)[1]
expected = "endstone_paradox." + ("dll" if args.platform == "windows" else "so")
if args.binary.name != expected or not args.binary.is_file():
    raise SystemExit(f"Expected tested binary {expected}")
args.output.mkdir(parents=True, exist_ok=True)
archive = args.output / f"paradox-{version}-{args.platform}-x86_64.zip"
documents = [
    "README.md",
    "LICENSE",
    "native/BUILDING.md",
    "native/MIGRATION.md",
    "native/MODULE_AUDIT.md",
    "native/VALIDATION.md",
    "native/RELEASE_NOTES.md",
    "native/references.lock.json",
]
documents += [
    p.relative_to(root).as_posix()
    for p in sorted((root / "native/validation").glob("*.json"))
]
documents += [
    str(p.relative_to(root)).replace("\\", "/")
    for p in sorted((root / "native/licenses").iterdir())
    if p.is_file()
]
with ZipFile(archive, "w", ZIP_DEFLATED) as output:
    output.write(args.binary, "plugins/" + expected)
    for relative in documents:
        output.write(root / relative, relative)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
print(archive)
