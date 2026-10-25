"""Verify the recorded Nana Space source fingerprints; not runtime qualification."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'docs/SOURCE_MANIFEST.json').read_text())
for relative, expected in manifest['files'].items():
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SystemExit(f'Missing or invalid source path: {relative}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Source fingerprint mismatch: {relative}')
print(f"Verified {len(manifest['files'])} source files; runtime state not asserted.")
