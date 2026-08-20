# Browser V8 reproduction tasks (Harbor + bench-v8)

This repo delivers **unified Harbor task packages**. It does **not** require
building the 65–70GB V8 images on a laptop.

Others can compile because every task uses the **same, pinned bench-v8
recipe** that ExploitBench already builds — not a homemade `gclient` Dockerfile.

## How compile is guaranteed without compiling here

| Layer | Who does it | What it proves |
|-------|-------------|----------------|
| Unified Harbor layout | this repo | Pipeline can load the task |
| Official `Dockerfile.template` at ExploitBench `9d0173bc` | this repo copies / bootstrap generates | The compile recipe is one that already works upstream |
| Pins: depot_tools `364ccfdd`, Harbor schema `1.3`, debian bookworm digest | `pins.toml` | Toolchain cannot drift |
| `bootstrap_v8.py` fills `tgt_commit` / `last_patch_commit` | minutes, **no V8 compile** | Revision pair is real, Dockerfile is no longer a placeholder |
| `python build_bugs.py` | Linux amd64 builder (~60 min, ~100 GB) | Actual `d8` images — optional for the author, required for the pipeline |

What this does **not** prove (and must not be faked):

- A 2022-era V8 still matching current grader text anchors — report as a patcher/build blocker, do not silently change the revision.
- That *your laptop* can finish ninja. Official target is Ubuntu x86_64 / `linux/amd64`.

The earlier `/v8/v8` `gclient` failure is exactly what this avoids: do not write a custom V8 fetch.

## Disk / time (when someone else compiles)

One CVE ⇒ one image, about **65–70GB**, about **60 minutes** on a fast workstation.
You do not need six images locally. Generate six **task directories**; compile one on a builder if a smoke check is requested.

## Layout

```
candidates/<CVE>/          # selection notes, flags, crbug (not agent-visible)
templates/harbor/          # single format for every task
tasks/browser-v8-<cve>/    # Harbor package (what the pipeline runs)
pins.toml                  # locked commits / CLI / schema
scripts/                   # generate + validate; does not rewrite bench-v8
```

Each task:

```
browser-v8-<cve>/
├── task.toml
├── instruction.md              # no CVE / patch / exploit
├── environment/
│   ├── Dockerfile              # bench-v8 recipe (after bootstrap)
│   ├── docker-compose.yaml
│   ├── task.yaml               # revision pair; not copied into agent image
│   ├── .factory/manifest.yaml
│   └── task-deps/
└── tests/
    ├── test.sh
    └── private/                # never COPY into the agent image
```

## Generate (no V8 compile)

```bash
python scripts/wrap_harbor_task.py CVE-2024-5830
python scripts/generate_all.py          # all candidates, same format
python scripts/validate_all.py
```

Fill the real compile Dockerfile (still no ninja):

```bash
python scripts/sync_upstream.py
# Linux: make -C third_party/exploitbench/benchmarks/bench-v8/mcp-server all
python scripts/bootstrap_bug.py CVE-2024-5830
python scripts/wrap_harbor_task.py CVE-2024-5830 --force
```

Optional, on a Linux amd64 machine with ~100GB free:

```bash
python scripts/build_inner.py CVE-2024-5830
```

## Pins

See `pins.toml`. Dedup against ExploitBench `TARGETS` at `9d0173bc` — these
candidates are new samples, not re-packaged existing bench-v8 bugs.
