"""Verify user-supplied server archives. Never downloads or redistributes BDS."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("archive", type=Path)
parser.add_argument("--platform", choices=("linux", "windows"), required=True)
args = parser.parse_args()
lock = json.loads((Path(__file__).parent.parent / "references.lock.json").read_text())
expected = lock["archives"][args.platform]
with args.archive.open("rb") as source:
    actual = hashlib.file_digest(source, "sha256").hexdigest()
if actual != expected["sha256"]:
    raise SystemExit("Archive does not match the supported BDS 1.26.51.1 build")
filename = "bedrock_server" + (".exe" if args.platform == "windows" else "")
with zipfile.ZipFile(args.archive) as archive:
    with archive.open(filename) as binary:
        actual_binary = hashlib.file_digest(binary, "sha256").hexdigest()
if actual_binary != expected["binary_sha256"]:
    raise SystemExit("Server executable checksum mismatch")
print(f"Verified {args.platform}: BDS {lock['server']}, protocol {lock['protocol']}")
