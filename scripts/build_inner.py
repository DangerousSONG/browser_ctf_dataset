#!/usr/bin/env python3
"""Build the inner bench-v8 image. Output stays on the build machine (~70GB)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_pins() -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    return tomllib.loads((ROOT / "pins.toml").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cve")
    parser.add_argument("--dev", action="store_true", help="faster non-reproducible build, no tar.zst")
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    pins = load_pins()
    bench = ROOT / pins["exploitbench"]["path"] / pins["exploitbench"]["bench_v8"]
    builder = bench / "build_bugs.py"
    if not builder.is_file():
        raise SystemExit("exploitbench missing; run python scripts/sync_upstream.py")
    argv = [sys.executable, str(builder)]
    if args.dev:
        argv.append("--dev")
    if args.no_export:
        argv.append("--no-export")
    argv.append(args.cve)
    print("+", " ".join(argv))
    print("Expect ~60 minutes and ~100 GB free disk. One CVE => one 65-70GB image.")
    return subprocess.call(argv, cwd=str(bench))


if __name__ == "__main__":
    sys.exit(main())
