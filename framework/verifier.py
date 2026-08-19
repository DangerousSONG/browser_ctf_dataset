#!/usr/bin/env python3
"""
Browser CTF 统一验证器
每个 CVE 目录独立验证
"""

import subprocess
import sys
import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class VerificationResult:
    task_id: str
    timestamp: str
    checks: Dict[str, bool]
    overall: str
    score: float
    logs: Dict[str, str]


class TaskVerifier:
    def __init__(self, task_path: str):
        self.task_path = Path(task_path)
        self.task_id = self.task_path.name
        self.task_yaml = self._load_task_yaml()
        self.results = {}
        self.logs = {}

    def _load_task_yaml(self) -> dict:
        yaml_path = self.task_path / "task.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"task.yaml not found in {self.task_path}")
        with open(yaml_path) as f:
            return yaml.safe_load(f)

    def _run_cmd(self, cmd: List[str], cwd: Optional[str] = None, timeout: int = 120) -> tuple:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd or str(self.task_path),
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -2, "", str(e)

    def check_files(self) -> bool:
        """Stage 0: 检查必要文件"""
        required = [
            "task.yaml", "Dockerfile", "run-tests.sh",
            "tests/test_vuln.py", "tests/test_func.py", "README.md"
        ]
        for f in required:
            if not (self.task_path / f).exists():
                self.logs["files"] = f"Missing: {f}"
                return False
        self.logs["files"] = "All required files present"
        return True

    def check_build(self) -> bool:
        """Stage 1: 构建 Docker 镜像"""
        image_tag = f"browser-ctf/{self.task_id}"
        ret, out, err = self._run_cmd(
            ["docker", "build", "-t", image_tag, "."],
            cwd=str(self.task_path),
            timeout=600
        )
        self.logs["build"] = out + err
        return ret == 0

    def check_env_ready(self) -> bool:
        """Stage 2: 环境就绪验证"""
        image_tag = f"browser-ctf/{self.task_id}"

        ret_func, out_func, _ = self._run_cmd([
            "docker", "run", "--rm", image_tag,
            "python3", "-m", "pytest", "tests/test_func.py", "-v"
        ])
        func_pass = ret_func == 0

        ret_vuln, out_vuln, _ = self._run_cmd([
            "docker", "run", "--rm", image_tag,
            "python3", "-m", "pytest", "tests/test_vuln.py", "-v"
        ])
        vuln_pass = ret_vuln == 0

        self.logs["env"] = f"func={func_pass}, vuln={vuln_pass}\n{out_func}\n{out_vuln}"
        return func_pass and vuln_pass

    def check_cve_ready(self) -> bool:
        """Stage 3: 端到端验证"""
        image_tag = f"browser-ctf/{self.task_id}"
        ret, out, err = self._run_cmd([
            "docker", "run", "--rm", image_tag,
            "bash", "run-tests.sh"
        ])
        self.logs["e2e"] = out + err
        return ret == 0

    def verify(self) -> VerificationResult:
        print(f"[+] Verifying {self.task_id}")

        checks = {
            "files": self.check_files(),
            "build": False,
            "env_ready": False,
            "cve_ready": False
        }

        if checks["files"]:
            checks["build"] = self.check_build()
        if checks["build"]:
            checks["env_ready"] = self.check_env_ready()
        if checks["env_ready"]:
            checks["cve_ready"] = self.check_cve_ready()

        score = sum(checks.values()) / len(checks) * 100
        overall = "PASS" if all(checks.values()) else "FAIL"

        result = VerificationResult(
            task_id=self.task_id,
            timestamp=datetime.now().isoformat(),
            checks=checks,
            overall=overall,
            score=score,
            logs=self.logs
        )

        report_path = self.task_path / "verify_report.json"
        with open(report_path, "w") as f:
            json.dump(asdict(result), f, indent=2)

        return result


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <cve-directory>")
        sys.exit(1)

    verifier = TaskVerifier(sys.argv[1])
    result = verifier.verify()

    print(f"\n{'='*60}")
    print(f"Result: {result.overall} ({result.score:.1f}%)")
    print(f"{'='*60}")
    for check, passed in result.checks.items():
        status = "✓" if passed else "✗"
        print(f"  [{status}] {check}")
    print(f"{'='*60}")
    sys.exit(0 if result.overall == "PASS" else 1)


if __name__ == "__main__":
    main()
