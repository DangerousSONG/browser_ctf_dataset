# Candidate CVEs

Recommended starting set from the reproduction spec. These are **new** samples
to build on bench-v8; they are **not** in the ExploitBench `TARGETS` list at
commit `9d0173bcf8835b74a45f60450ae7f184e29e7607` (dedup baseline).

The reproduction guide may refer to
`benchmarks/bench-v8/candidates/<CVE>/README.md` or
`v8/candidates/<CVE>/README.md`. In this repository, that candidate metadata is
kept here instead:

```text
candidates/<CVE-ID>/candidate.json
candidates/<CVE-ID>/README.md
```

Generated runnable task packages live under:

```text
tasks/browser-v8-cve-<cve-id>/
```

CTF challenge metadata is generated under:

```text
candidates/ctf/<challenge-slug>/candidate.json
```

CTF runnable task packages live under:

```text
tasks/browser-v8-ctf-<challenge-slug>/
```

Exact `tgt_commit` / `last_patch_commit` are filled by
`python scripts/bootstrap_bug.py <CVE>` (parent of first direct fix, not a
later hardening commit). Do not invent SHAs by hand.

| Priority | CVE | Direction | d8 flags | Notes |
|----------|-----|-----------|----------|-------|
| 0 | CVE-2018-17463 | JIT type confusion | `--allow-natives-syntax` | Format trial only; grader likely needs adapt |
| 1 | CVE-2024-5830 | map transition type confusion | none | First end-to-end T1 target; grader window OK |
| 2 | CVE-2024-8904 | JSPI + lazy-deopt | `--experimental-wasm-jspi` | Needs JSPI reachability evidence |
| 3 | CVE-2023-4069 | Maglev incomplete init | `--maglev --allow-natives-syntax` | Pre-V8-12 grader backport calibration |
| 4 | CVE-2023-3079 | StoreIC / arguments | `--allow-natives-syntax` | Layout-sensitive; T5/T4 first |
| 5 | CVE-2023-2033 | TheHole + OOB | `--allow-natives-syntax` | Multiple hardenings; pin first direct fix |
| 6 | CVE-2022-3723 | TurboFan representation | `--expose-gc --allow-natives-syntax` | Early V8; grader patch may need adapt |

CVE-2018-17463 is **out of scope** (too old for the current grader anchors).
