#!/usr/bin/env python3
"""Render a Harbor task package from candidates/ + templates.

Does not bake tests/private into environment/Dockerfile.
If bench-v8 already generated bugs/<CVE>/, copies the inner Dockerfile
into environment/task-deps/inner/ for a source-buildable submission.
"""
from __future__ import annotations

import json
import shutil
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "harbor"


def load_pins() -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    return tomllib.loads((ROOT / "pins.toml").read_text(encoding="utf-8"))


def load_candidate(cve: str) -> dict:
    path = ROOT / "candidates" / cve / "candidate.json"
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def slug(cve: str) -> str:
    return cve.lower()


def image_tag(cve: str) -> str:
    return cve.lower()


def bench_v8_image(cve: str) -> str:
    return image_tag(cve)


def render(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace("{" + key + "}", value)
    return text


def render_sources(sources: list[dict]) -> str:
    if not sources:
        return "- pending source record"
    rows = []
    for source in sources:
        title = source.get("title") or "source"
        url = source.get("url") or ""
        rows.append(f"- {title}: {url}".rstrip())
    return "\n".join(rows)


def copy_tree(src: Path, dst: Path, mapping: dict[str, str]) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if path.name == ".gitkeep":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            continue
        data = path.read_text(encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(data, mapping), encoding="utf-8")
        if path.suffix == ".sh" or path.name.endswith(".py"):
            target.chmod(target.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def maybe_copy_inner(cve: str, dest: Path) -> None:
    pins = load_pins()
    bugs = ROOT / pins["exploitbench"]["path"] / pins["exploitbench"]["bench_v8"] / "bugs" / cve
    if not bugs.is_dir():
        return
    inner = dest / "environment" / "task-deps" / "inner"
    if inner.exists():
        shutil.rmtree(inner)
    shutil.copytree(bugs, inner, ignore=shutil.ignore_patterns("mcp-server"))
    note = dest / "environment" / "task-deps" / "INNER.md"
    note.write_text(
        "Copied from bench-v8 bugs/{cve}/ after bootstrap.\n"
        "Build with: python scripts/build_inner.py {cve}\n"
        "Do not COPY tests/private into this context.\n".format(cve=cve),
        encoding="utf-8",
    )
    print(f"[+] copied inner build context -> {inner}")


def load_bootstrap_task(cve: str) -> dict:
    pins = load_pins()
    task_json = (
        ROOT
        / pins["exploitbench"]["path"]
        / pins["exploitbench"]["bench_v8"]
        / "bugs"
        / cve
        / "task.json"
    )
    if not task_json.is_file():
        return {}
    return json.loads(task_json.read_text(encoding="utf-8"))


def preserve_private_evidence(dest: Path) -> tempfile.TemporaryDirectory[str] | None:
    evidence = dest / "tests" / "private" / "tier-evidence"
    if not evidence.exists():
        return None
    tmp = tempfile.TemporaryDirectory(prefix="browser-ctf-evidence-")
    shutil.copytree(evidence, Path(tmp.name) / "tier-evidence")
    return tmp


def restore_private_evidence(saved: tempfile.TemporaryDirectory[str] | None, dest: Path) -> None:
    if saved is None:
        return
    src = Path(saved.name) / "tier-evidence"
    if not src.exists():
        return
    dst = dest / "tests" / "private" / "tier-evidence"
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in {".gitkeep", "README.md"}:
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("cve")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cand = load_candidate(args.cve)
    boot = load_bootstrap_task(args.cve)
    task_slug = slug(args.cve)
    dest = ROOT / "tasks" / f"browser-v8-{task_slug}"
    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} exists; pass --force to overwrite")
    saved_evidence = preserve_private_evidence(dest) if args.force else None
    if dest.exists():
        shutil.rmtree(dest)

    mapping = {
        "cve": args.cve,
        "task_slug": task_slug,
        "image_tag": image_tag(args.cve),
        "bench_v8_image": bench_v8_image(args.cve),
        "declared_tier_goal": cand.get("declared_tier_goal") or "T3",
        "min_accepted_tier": cand.get("min_accepted_tier") or "T3",
        "direction": cand.get("direction") or "pending analysis",
        "recommended_as": cand.get("recommended_as") or "candidate",
        "chrome_fixed_version": cand.get("chrome_fixed_version") or "unknown",
        "grader_range": cand.get("grader_range") or "unknown",
        "notes": cand.get("notes") or "",
        "sources_markdown": render_sources(cand.get("sources") or []),
        "crbug": str(cand.get("crbug") or ""),
        "tgt_commit": str(cand.get("tgt_commit") or boot.get("tgt_commit") or "PENDING_BOOTSTRAP"),
        "last_patch_commit": str(cand.get("last_patch_commit") or boot.get("last_patch_commit") or "PENDING_BOOTSTRAP"),
        "eval_flags_json": json.dumps(cand.get("eval_flags") if cand.get("eval_flags") is not None else boot.get("eval_flags", [])),
    }
    copy_tree(TEMPLATE, dest, mapping)
    restore_private_evidence(saved_evidence, dest)
    if saved_evidence is not None:
        saved_evidence.cleanup()
    maybe_copy_inner(args.cve, dest)
    print(f"[+] wrote {dest}")
    print("    Unified Harbor format; instruction.md has no CVE id.")
    print("    Compile recipe: environment/task-deps/BUILD.txt (no local ninja).")
    if (dest / "environment" / "task-deps" / "inner" / "Dockerfile").exists():
        print("    Inner bench-v8 Dockerfile present — others can build_inner.")
    else:
        print("    Inner Dockerfile pending bootstrap (still no V8 compile):")
        print("      python scripts/bootstrap_bug.py", args.cve)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
