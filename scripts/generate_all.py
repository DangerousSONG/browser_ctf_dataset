#!/usr/bin/env python3
"""Generate every candidate into the same Harbor layout. No V8 compile."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAP = ROOT / "scripts" / "wrap_harbor_task.py"


def candidates() -> list[str]:
    rows = []
    for path in sorted((ROOT / "candidates").glob("CVE-*/candidate.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append((int(data.get("priority") or 99), data["cve"]))
    rows.sort()
    return [cve for _, cve in rows]


def main() -> int:
    rc = 0
    for cve in candidates():
        cmd = [sys.executable, str(WRAP), cve, "--force"]
        print("+", " ".join(cmd))
        rc = subprocess.call(cmd) or rc
    print("\nValidate with: python scripts/validate_all.py")
    print("Bootstrap (still no ninja): python scripts/bootstrap_bug.py <CVE>")
    return rc


if __name__ == "__main__":
    sys.exit(main())
