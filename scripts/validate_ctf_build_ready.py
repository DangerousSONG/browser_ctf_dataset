#!/usr/bin/env python3
"""Validate CTF browser/V8 task packages.

For CTF tasks, build-ready means the package contains the original challenge
source payload and a Docker/compose smoke-check wrapper. It is intentionally
separate from validate_build_ready.py, which validates CVE revision-pair
bench-v8 packages.
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEAK_RE = re.compile(
    r"(^|[/\\])("
    r"checker|checkers|writeup|writeups|solution|solutions|solve|solves|"
    r"exploit|exploits"
    r")($|[/\\])|"
    r"(^|[/\\])(flags?(?:$|[._-].*|\.txt)|writeup\.md|solution(?:[._-].*)?\.[^\\/]+|"
    r"exploit(?:[._-].*)?\.[^\\/]+|expl(?:[._-].*)?\.[^\\/]+)$",
    re.I,
)

REQUIRED = [
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "environment/docker-compose.yaml",
    "environment/task.yaml",
    "environment/.factory/manifest.yaml",
    "environment/task-deps/BUILD.txt",
    "environment/task-deps/README.md",
    "environment/task-deps/INNER.md",
    "environment/task-deps/inner",
    "tests/test.sh",
    "tests/private/verify.sh",
    "tests/private/solution.sh",
    "tests/private/capability_contract.json",
    "tests/private/harness/run_submission.py",
]


def task_dirs() -> list[Path]:
    return sorted(p for p in (ROOT / "tasks").glob("browser-v8-ctf-*") if p.is_dir())


def check_task(path: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (path / rel).exists():
            errors.append(f"missing {rel}")

    task_yaml = path / "environment" / "task.yaml"
    if task_yaml.exists():
        text = task_yaml.read_text(encoding="utf-8")
        for token in ("source_type: ctf", "source_repo:", "source_path:", "source_file_count:"):
            if token not in text:
                errors.append(f"environment/task.yaml missing {token}")

    challenge = path / "environment" / "task-deps" / "inner"
    if challenge.exists():
        files = [p for p in challenge.rglob("*") if p.is_file()]
        if not files:
            errors.append("challenge source directory is empty")
        leaked = [
            p
            for p in files
            if LEAK_RE.search(str(p.relative_to(challenge)))
        ]
        if leaked:
            errors.append(f"challenge source appears to contain solution/writeup artifacts: {leaked[0].relative_to(path)}")

    dockerfile = path / "environment" / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text(encoding="utf-8")
        if "COPY task-deps/inner /challenge" not in text:
            errors.append("Dockerfile must copy task-deps/inner to /challenge")

    compose = path / "environment" / "docker-compose.yaml"
    if compose.exists():
        text = compose.read_text(encoding="utf-8")
        if "verify:" not in text or "/tests/test.sh" not in text:
            errors.append("docker-compose.yaml must expose verify service running /tests/test.sh")
        if "../tests:/tests:ro" not in text:
            errors.append("docker-compose.yaml must mount tests read-only")

    return errors


def main() -> int:
    dirs = task_dirs()
    if not dirs:
        print("No tasks/browser-v8-ctf-* directories found.")
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
