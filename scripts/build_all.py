#!/usr/bin/env python3
"""
批量构建所有 CVE Docker 镜像
"""

import subprocess
import sys
from pathlib import Path


def build_all():
    root = Path(".")
    cve_dirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith("cve-")])

    results = []
    for d in cve_dirs:
        image_tag = f"browser-ctf/{d.name}"
        print(f"\n{'='*60}")
        print(f"Building {d.name} -> {image_tag}")
        print(f"{'='*60}")

        result = subprocess.run(
            ["docker", "build", "-t", image_tag, "."],
            cwd=str(d),
            capture_output=False
        )
        results.append((d.name, result.returncode == 0))

    print(f"\n{'='*60}")
    print("Build Summary")
    print(f"{'='*60}")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\nTotal: {len(results)}, Passed: {passed}")

    return all(ok for _, ok in results)


if __name__ == "__main__":
    success = build_all()
    sys.exit(0 if success else 1)
