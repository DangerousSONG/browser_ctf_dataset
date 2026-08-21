#!/usr/bin/env python3
"""Check whether generated task packages are ready for a real bench-v8 build.

This does not prove compilation succeeded. It proves the package has moved
past placeholder metadata and contains the bootstrapped bench-v8 build context
needed by a Linux amd64 builder.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def task_dirs() -> list[Path]:
    return sorted(p for p in (ROOT / "tasks").glob("browser-v8-cve-*") if p.is_dir())


def check_task(path: Path) -> list[str]:
    errors: list[str] = []
    task_yaml = path / "environment" / "task.yaml"
    if not task_yaml.exists():
        errors.append("missing environment/task.yaml")
    else:
        text = task_yaml.read_text(encoding="utf-8")
        if "PENDING_BOOTSTRAP" in text:
            errors.append("revision pair is still PENDING_BOOTSTRAP")

    inner = path / "environment" / "task-deps" / "inner"
    if not (inner / "Dockerfile").exists():
        errors.append("missing bootstrapped inner/Dockerfile")
    if not (inner / "task.json").exists():
        errors.append("missing bootstrapped inner/task.json")
    else:
        try:
            task = json.loads((inner / "task.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"inner/task.json is invalid JSON: {exc}")
        else:
            for key in ("tgt_commit", "last_patch_commit"):
                if not task.get(key):
                    errors.append(f"inner/task.json missing {key}")
            if not task.get("eval_flags", []) and "eval_flags" not in task:
                errors.append("inner/task.json missing eval_flags")

    return errors


def main() -> int:
    dirs = task_dirs()
    if not dirs:
        print("No tasks/browser-v8-cve-* directories found.")
        return 1

    failed = 0
    for path in dirs:
        errors = check_task(path)
        if errors:
            failed += 1
            print(f"[NOT READY] {path.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[READY] {path.name}")

    print(f"\nTotal: {len(dirs)}, Ready: {len(dirs) - failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
