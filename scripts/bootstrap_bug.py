#!/usr/bin/env python3
"""Thin wrapper around bench-v8 bootstrap_v8.py. Does not rewrite the base."""
from __future__ import annotations

import argparse
import json
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


def load_candidate(cve: str) -> dict:
    path = ROOT / "candidates" / cve / "candidate.json"
    if not path.is_file():
        raise SystemExit(f"unknown candidate: {cve} (add candidates/{cve}/candidate.json)")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cve", help="e.g. CVE-2024-5830")
    parser.add_argument("--commit", default=None, help="last-patch SHA (first direct fix)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    pins = load_pins()
    cand = load_candidate(args.cve)
    eb = ROOT / pins["exploitbench"]["path"]
    bench = eb / pins["exploitbench"]["bench_v8"]
    bootstrap = bench / "env-builder" / "bootstrap_v8.py"
    mcp = bench / "mcp-server" / "server"
    if not bootstrap.is_file():
        raise SystemExit("exploitbench missing; run: python scripts/sync_upstream.py")
    if not mcp.is_file():
        raise SystemExit("mcp-server binary missing; run: make -C third_party/exploitbench/benchmarks/bench-v8/mcp-server all")

    argv = [
        sys.executable,
        str(bootstrap),
        "--force" if args.force else "",
        "--depot-tools-commit",
        pins["depot_tools"]["commit"],
    ]
    argv = [a for a in argv if a]
    for flag in cand.get("eval_flags") or []:
        argv.append(f"--eval-flag={flag}")
    argv += ["bug", args.cve]
    crbug = cand.get("crbug")
    if crbug:
        argv += ["--pair", f"b/{crbug}"]
    commit = args.commit or cand.get("last_patch_commit")
    if commit:
        argv += ["--commit", commit]
    print("+", " ".join(argv))
    return subprocess.call(argv, cwd=str(bench / "env-builder"))


if __name__ == "__main__":
    sys.exit(main())
