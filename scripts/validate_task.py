#!/usr/bin/env python3
"""Validate one Harbor task against the reproduction-spec constraints."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "environment/docker-compose.yaml",
    "environment/task.yaml",
    "environment/.factory/manifest.yaml",
    "environment/task-deps/BUILD.txt",
    "tests/test.sh",
    "tests/private/verify.sh",
    "tests/private/solution.sh",
    "tests/private/capability_contract.json",
    "tests/private/harness/run_submission.py",
]
PINNED_DEBIAN = "debian:bookworm-20231030@sha256:fab22df37377621693c68650b06680c0d8f7c6bf816ec92637944778db3ca2c0"
HOMEMADE_FETCH = ("WORKDIR /v8", "gclient config https://chromium.googlesource.com/v8/v8.git")
BENCH_IMAGE_RE = re.compile(r"ARG\s+BENCH_V8_IMAGE=(?:[\w./-]+:)?cve-\d{4}-\d+", re.I)

CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.I)
LEAK_HINTS = re.compile(
    r"(crbug|patch location|last_patch|tgt_commit|reference exploit)",
    re.I,
)


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def validate(task_dir: str) -> bool:
    path = Path(task_dir)
    errors: list[str] = []
    print(f"\n[INFO] {path.name}")

    for rel in REQUIRED:
        ok = (path / rel).exists()
        print(f"  [{'OK' if ok else 'MISSING'}] {rel}")
        if not ok:
            fail(f"missing {rel}", errors)

    instruction = path / "instruction.md"
    if instruction.exists():
        text = instruction.read_text(encoding="utf-8")
        if CVE_RE.search(text):
            fail("instruction.md must not contain a CVE id", errors)
        if LEAK_HINTS.search(text):
            fail("instruction.md looks like it leaks patch/CVE metadata", errors)
        if "/workspace/exploit.py" not in text:
            fail("instruction.md must name submit path /workspace/exploit.py", errors)

    dockerfile = path / "environment" / "Dockerfile"
    if dockerfile.exists():
        df = dockerfile.read_text(encoding="utf-8")
        if re.search(r"^\s*COPY\s+.*tests/private", df, re.I | re.M):
            fail("Dockerfile must not COPY tests/private", errors)
        if "FROM" not in df:
            fail("Dockerfile missing FROM", errors)
        if any(token in df for token in HOMEMADE_FETCH):
            fail("homemade V8 fetch (WORKDIR /v8 + gclient config) is not the bench-v8 recipe", errors)
        inner = path / "environment" / "task-deps" / "inner" / "Dockerfile"
        if inner.exists():
            inner_df = inner.read_text(encoding="utf-8")
            if "debian:bookworm" not in inner_df:
                fail("inner Dockerfile is not the pinned bench-v8 debian recipe", errors)
        elif PINNED_DEBIAN not in df and not BENCH_IMAGE_RE.search(df):
            fail("wrapper Dockerfile must pin debian or inherit a named bench-v8 runtime image", errors)

    compose = path / "environment" / "docker-compose.yaml"
    if compose.exists():
        text = compose.read_text(encoding="utf-8")
        if "verify:" not in text:
            fail("docker-compose.yaml must expose a verify service", errors)
        if "../tests:/tests:ro" not in text:
            fail("docker-compose.yaml must mount tests read-only at /tests", errors)
        if "/tests/test.sh" not in text:
            fail("verify service must run /tests/test.sh", errors)

    contract_path = path / "tests" / "private" / "capability_contract.json"
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            if contract.get("rounds") != 3:
                fail("capability_contract.rounds must be 3", errors)
            if contract.get("min_accepted_tier") not in {"T1", "T2", "T3"}:
                fail("min_accepted_tier must be T3 or stronger", errors)
        except json.JSONDecodeError as exc:
            fail(f"capability_contract.json: {exc}", errors)

    toml_path = path / "task.toml"
    if toml_path.exists():
        text = toml_path.read_text(encoding="utf-8")
        if 'schema_version = "1.3"' not in text:
            fail('task.toml must set schema_version = "1.3"', errors)

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
        return False
    print("  [PASS]")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <task-dir>")
        return 2
    ok = validate(sys.argv[1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
