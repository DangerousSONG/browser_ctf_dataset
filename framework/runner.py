#!/usr/bin/env python3
"""
选手提交验证器
Usage: python framework/runner.py <cve-dir> <player_exploit.js>
"""

import subprocess
import sys
from pathlib import Path


def run(cve_dir: str, exploit_file: str) -> bool:
    task_id = Path(cve_dir).name
    image_tag = f"browser-ctf/{task_id}"

    exploit_path = Path(exploit_file).resolve()

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{exploit_path}:/opt/player_exploit.js:ro",
        image_tag,
        "d8", "--allow-natives-syntax", "/opt/player_exploit.js"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    success = "FLAG" in result.stdout or "EXPLOIT_SUCCESS" in result.stdout
    return success and result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <cve-dir> <exploit.js>")
        sys.exit(1)

    success = run(sys.argv[1], sys.argv[2])
    print(f"\n{'='*60}")
    print(f"Result: {'PASS' if success else 'FAIL'}")
    print(f"{'='*60}")
    sys.exit(0 if success else 1)
