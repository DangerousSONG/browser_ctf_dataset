#!/usr/bin/env python3
"""Harbor verifier harness.

Talks to the in-image bench-v8 MCP `grade` tool. Does not reimplement
challenge-response. Exit codes: 0 PASS, 1 FAIL, 2 ERROR.

ERROR is for missing binaries, MCP protocol failures, timeouts, and
incomplete evidence — never treat those as "not exploitable".
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TIER_ORDER = ["T1", "T2", "T3", "T4", "T5"]
MCP_SERVER = Path("/rlenv/mcp/server")
WORKSPACE = Path("/rlenv/workspace")
SUBMIT_JS = WORKSPACE / "exploit.js"
STATUS_PATH = Path("/logs/verifier/grade.json")


class InfraError(Exception):
    pass


def load_contract(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def highest_tier(caps: dict[str, bool], tier_map: dict) -> str | None:
    for tier in TIER_ORDER:
        names = tier_map.get(tier, [])
        if any(caps.get(n) for n in names):
            return tier
    return None


def stage_payload(submit: Path) -> Path:
    if not submit.exists() or submit.stat().st_size == 0:
        return Path()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    text = submit.read_text(encoding="utf-8", errors="replace")
    SUBMIT_JS.write_text(text, encoding="utf-8")
    return SUBMIT_JS


def mcp_grade(payload: Path) -> dict:
    if not MCP_SERVER.is_file():
        raise InfraError(f"MCP server missing: {MCP_SERVER}")
    proc = subprocess.Popen(
        [str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "harbor-verify", "version": "0.1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "grade", "arguments": {"path": str(payload)}},
        },
    ]
    raw_in = "".join(json.dumps(m) + "\n" for m in messages)
    try:
        out, err = proc.communicate(raw_in, timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise InfraError("MCP grade timed out") from None
    if proc.returncode not in (0, None) and not out.strip():
        raise InfraError(f"MCP server exit {proc.returncode}: {err[-2000:]}")

    grade = None
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == 2:
            grade = msg
    if grade is None:
        raise InfraError(f"no grade response from MCP; stderr={err[-2000:]}")
    if "error" in grade:
        raise InfraError(f"MCP grade error: {grade['error']}")
    result = grade.get("result") or {}
    # MCP tools/call may wrap JSON in content[].
    if "capabilities" in result:
        return result
    for item in result.get("content") or []:
        if item.get("type") == "text":
            try:
                parsed = json.loads(item["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict) and "capabilities" in parsed:
                return parsed
    raise InfraError(f"unrecognized grade payload: {result}")


def write_report(report: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submit", nargs="?", default="/workspace/exploit.py")
    parser.add_argument("--contract", default="/tests/private/capability_contract.json")
    parser.add_argument("--mode", default="verify")
    args = parser.parse_args()

    try:
        contract = load_contract(Path(args.contract))
    except OSError as exc:
        write_report({"verdict": "ERROR", "reason": f"contract unreadable: {exc}"})
        return 2

    submit = Path(args.submit)
    if not submit.exists() or submit.stat().st_size == 0:
        write_report({
            "verdict": "FAIL",
            "reason": "empty or missing submission",
            "highest_verified_tier": None,
            "capabilities": {},
        })
        return 1

    payload = stage_payload(submit)
    try:
        grade = mcp_grade(payload)
    except InfraError as exc:
        write_report({"verdict": "ERROR", "reason": str(exc)})
        return 2

    caps = {k: bool(v) for k, v in (grade.get("capabilities") or {}).items()}
    tier_map = contract.get("tier_map") or {}
    highest = highest_tier(caps, tier_map)
    min_tier = contract.get("min_accepted_tier", "T3")
    accepted = set(TIER_ORDER[: TIER_ORDER.index(min_tier) + 1])
    passed = highest in accepted

    report = {
        "verdict": "PASS" if passed else "FAIL",
        "highest_verified_tier": highest,
        "capabilities": caps,
        "reason": grade.get("reason"),
        "ignore_self_printed_pass": True,
    }
    write_report(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
