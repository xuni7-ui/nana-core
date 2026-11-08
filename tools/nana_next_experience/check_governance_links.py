"""Check local targets in the governance source map; no runtime or network access."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/nana_next_experience/GOVERNANCE_SOURCE_MAP.md"


def main():
    links = re.findall(r"\]\(([^)]+)\)", DOCUMENT.read_text(encoding="utf-8"))
    missing = []
    checked = 0
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        checked += 1
        target = unquote(link.split("#", 1)[0])
        if not (DOCUMENT.parent / target).exists():
            missing.append(link)
    if missing:
        print("Missing local targets:", *missing, sep="\n")
        return 1
    print(f"OK: {checked} local targets checked (external URLs and anchors excluded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
