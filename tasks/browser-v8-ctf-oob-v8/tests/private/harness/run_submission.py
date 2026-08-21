#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

challenge = Path(os.environ.get("CTF_CHALLENGE_DIR", "/challenge"))
submit = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/workspace/exploit.py")
files = [p for p in challenge.rglob("*") if p.is_file()]

if not challenge.is_dir() or not files:
    print("ERROR: challenge source is missing")
    Path("/logs/verifier/status.txt").write_text("ERROR\n")
    Path("/logs/verifier/reward.txt").write_text("0\n")
    raise SystemExit(2)

print(f"READY: challenge source mounted at {challenge} ({len(files)} files)")
print(f"SUBMIT: {submit}")
Path("/logs/verifier/status.txt").write_text("READY\n")
Path("/logs/verifier/reward.txt").write_text("0\n")
raise SystemExit(0)
