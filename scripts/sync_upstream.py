#!/usr/bin/env python3
"""Clone exploitbench at the pin in pins.toml."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_pins() -> dict:
    path = ROOT / "pins.toml"
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    return tomllib.loads(text)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def main() -> int:
    pins = load_pins()
    spec = pins["exploitbench"]
    dest = ROOT / spec["path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    commit = spec["commit"]
    if not (dest / ".git").exists():
        run(["git", "clone", spec["repo"], str(dest)])
    run(["git", "fetch", "--all"], cwd=dest)
    run(["git", "checkout", "--detach", commit], cwd=dest)
    print(f"[ok] exploitbench @ {commit} -> {dest}")
    print("Next: cd third_party/exploitbench/benchmarks/bench-v8/mcp-server && make all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
