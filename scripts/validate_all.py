#!/usr/bin/env python3
"""
批量验证所有 CVE 目录
"""

import os
import sys
import yaml
from pathlib import Path

REQUIRED_FILES = [
    "task.yaml", "Dockerfile", "run-tests.sh",
    "tests/test_vuln.py", "tests/test_func.py", "README.md",
]


def validate(cve_dir: str) -> bool:
    path = Path(cve_dir)
    if not path.is_dir():
        return False

    # 跳过非 CVE 目录
    if not path.name.startswith("cve-"):
        return True

    print(f"\n[INFO] Validating {path.name}...")

    all_ok = True
    for f in REQUIRED_FILES:
        exists = (path / f).exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {f}")
        if not exists:
            all_ok = False

    # 校验 task.yaml
    yaml_path = path / "task.yaml"
    if yaml_path.exists():
        try:
            with open(yaml_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            for key in ["instruction", "difficulty", "category", "tags", "parser_name"]:
                if key not in data:
                    print(f"  [MISSING KEY] task.yaml: {key}")
                    all_ok = False
        except Exception as e:
            print(f"  [ERROR] task.yaml: {e}")
            all_ok = False

    # 校验 Dockerfile
    df = path / "Dockerfile"
    if df.exists():
        content = df.read_text(encoding="utf-8")
        if "FROM" not in content:
            print(f"  [INVALID] Dockerfile missing FROM")
            all_ok = False

    status = "PASS" if all_ok else "FAIL"
    print(f"  [{status}] {path.name}")
    return all_ok


def main():
    root = Path(".")
    cve_dirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith("cve-")])

    if not cve_dirs:
        print("No cve-* directories found.")
        sys.exit(1)

    print(f"Found {len(cve_dirs)} CVE task(s)")

    results = []
    for d in cve_dirs:
        results.append((d.name, validate(str(d))))

    print(f"\n{'='*60}")
    print("Validation Summary")
    print(f"{'='*60}")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status:12s} {name}")
    print(f"\nTotal: {len(results)}, Passed: {passed}")
    print(f"{'='*60}")

    sys.exit(0 if all(ok for _, ok in results) else 1)


if __name__ == "__main__":
    main()
