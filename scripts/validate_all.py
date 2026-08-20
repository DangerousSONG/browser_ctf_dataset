#!/usr/bin/env python3
"""Validate every tasks/browser-v8-* package."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_task import validate  # noqa: E402


def main() -> int:
    tasks_root = ROOT / "tasks"
    dirs = sorted(p for p in tasks_root.glob("browser-v8-*") if p.is_dir())
    if not dirs:
        print("No tasks/browser-v8-* directories found.")
        return 1
    results = [(d.name, validate(str(d))) for d in dirs]
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\nTotal: {len(results)}, Passed: {passed}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
