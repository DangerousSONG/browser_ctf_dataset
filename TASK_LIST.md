# 已完成任务清单

本文档记录当前仓库已经整理成 build-ready 目录的 CVE 与 CTF 任务。

当前状态：

- CVE 任务：7 个，全部通过结构校验和 CVE build-ready 校验。
- CTF 任务：38 个，全部通过 CTF build-ready 校验。
- 总任务数：45 个，`python scripts/validate_all.py` 期望结果为 `Total: 45, Passed: 45`。
- 已完整本机编译并用 docker compose 启动验证的样例：`CVE-2024-5830`。

## CVE 任务列表

| CVE | 任务目录 | 方向 | Chrome 修复版本 |
| --- | --- | --- | --- |
| CVE-2018-17463 | `tasks/browser-v8-cve-2018-17463` | JIT type confusion via incorrect CreateObject side-effect | 70.0.3497.81 |
| CVE-2022-3723 | `tasks/browser-v8-cve-2022-3723` | TurboFan representation type confusion (in-the-wild) | 106.0.5249.119 |
| CVE-2023-2033 | `tasks/browser-v8-cve-2023-2033` | TheHole export and OOB | 112.0.5615.121 |
| CVE-2023-3079 | `tasks/browser-v8-cve-2023-3079` | StoreIC / arguments type confusion | 114.0.5735.110 |
| CVE-2023-4069 | `tasks/browser-v8-cve-2023-4069` | Maglev incomplete object initialization | 115.0.5790.170 |
| CVE-2024-5830 | `tasks/browser-v8-cve-2024-5830` | object map transition type confusion | 126.0.6478.54 |
| CVE-2024-8904 | `tasks/browser-v8-cve-2024-8904` | JSPI and lazy-deopt type confusion | 129.0.6668.58 |

## CTF 任务列表

| 题目 | 赛事 | 年份 | 任务目录 |
| --- | --- | --- | --- |
| Baby Array.xor | openECSC | 2024 | `tasks/browser-v8-ctf-baby-array-xor` |
| BabyChrome | LINE CTF | 2021 | `tasks/browser-v8-ctf-babychrome` |
| Baby WASM | RITSEC CTF | 2021 | `tasks/browser-v8-ctf-baby-wasm` |
| Backfired | openECSC | 2024 | `tasks/browser-v8-ctf-backfired` |
| chromatic_aberration | CONFidence CTF | 2020 | `tasks/browser-v8-ctf-chromatic-aberration` |
| d8 | Google CTF | 2022 | `tasks/browser-v8-ctf-d8` |
| Date | KITCTFCTF | 2022 | `tasks/browser-v8-ctf-date` |
| DeadV8 Sandbox | DeadSec CTF | 2025 | `tasks/browser-v8-ctf-deadv8-sandbox` |
| Download Horsepower | picoCTF | 2021 | `tasks/browser-v8-ctf-download-horsepower` |
| E-Corp Part 2 | UTCTF | 2025 | `tasks/browser-v8-ctf-e-corp-part-2` |
| Fourchain Hole | HITCON CTF | 2022 | `tasks/browser-v8-ctf-fourchain-hole` |
| Half Promise | 0CTF/TCTF | 2023 | `tasks/browser-v8-ctf-half-promise` |
| HEAT | Google CTF | 2024 | `tasks/browser-v8-ctf-heat` |
| Is this pwn or web? | DownUnderCTF | 2020 | `tasks/browser-v8-ctf-is-this-pwn-or-web` |
| Just In Time | Google CTF | 2018 | `tasks/browser-v8-ctf-just-in-time` |
| Kit Engine | picoCTF | 2021 | `tasks/browser-v8-ctf-kit-engine` |
| Krautflare | 35C3 CTF | 2018 | `tasks/browser-v8-ctf-krautflare` |
| memory-hole | DiceCTF | 2022 | `tasks/browser-v8-ctf-memory-hole` |
| OOB-V8 | *CTF | 2019 | `tasks/browser-v8-ctf-oob-v8` |
| Optimal Vee Ate | DownUnderCTF | 2022 | `tasks/browser-v8-ctf-optimal-vee-ate` |
| Promise | 0CTF/TCTF | 2023 | `tasks/browser-v8-ctf-promise` |
| Roll a D8 | PlaidCTF | 2018 | `tasks/browser-v8-ctf-roll-a-d8` |
| Teen WASM | RITSEC CTF | 2021 | `tasks/browser-v8-ctf-teen-wasm` |
| The False Promise | PlaidCTF | 2021 | `tasks/browser-v8-ctf-the-false-promise` |
| triforce | TRX CTF | 2026 | `tasks/browser-v8-ctf-triforce` |
| triforce-sbx | TRX CTF | 2026 | `tasks/browser-v8-ctf-triforce-sbx` |
| Turboflan | picoCTF | 2021 | `tasks/browser-v8-ctf-turboflan` |
| Typer | CrewCTF | 2023 | `tasks/browser-v8-ctf-typer` |
| Übercaged | SAS CTF | 2024 | `tasks/browser-v8-ctf-ubercaged` |
| v8box | Google CTF | 2023 | `tasks/browser-v8-ctf-v8box` |
| V8box | BackdoorCTF | 2024 | `tasks/browser-v8-ctf-v8box-backdoorctf` |
| v8CTF Chrome 150 | v8CTF | 2026 | `tasks/browser-v8-ctf-v8ctf-chrome-150` |
| v8CTF Chrome 151 | v8CTF | 2026 | `tasks/browser-v8-ctf-v8ctf-chrome-151` |
| V8 for dummies 1 | ASIS CTF Quals | 2021 | `tasks/browser-v8-ctf-v8-for-dummies-1` |
| V8 SBX | HITCON CTF | 2024 | `tasks/browser-v8-ctf-v8-sbx` |
| V8 SBX Revenge | HITCON CTF | 2024 | `tasks/browser-v8-ctf-v8-sbx-revenge` |
| vroom_vroom | DownUnderCTF | 2023 | `tasks/browser-v8-ctf-vroom-vroom` |
| WatTheWasm | Google CTF | 2023 | `tasks/browser-v8-ctf-watthewasm` |

## CTF 的构建教程和 CVE 一样吗

结论：外层操作很像，但底层准备流程不一样。

CVE 任务通常分两步：

1. 先构建真实的 bench-v8 底层镜像。
2. 再进入对应任务的 `environment/` 目录，用 docker compose 构建和运行 Harbor 包装层。

示例：

```powershell
python scripts/build_inner.py CVE-2024-5830 --dev --no-export
docker tag cve-2024-5830-dev:latest cve-2024-5830:latest
cd D:\Code\browser_ctf_dataset\tasks\browser-v8-cve-2024-5830\environment
docker compose build
docker compose run --rm verify
```

CTF 任务不走 `scripts/build_inner.py`。CTF 的原始题目文件已经放在：

```text
tasks/browser-v8-ctf-<challenge-slug>/environment/task-deps/inner/
```

所以 CTF 的外层构建方式是：

```powershell
cd D:\Code\browser_ctf_dataset\tasks\browser-v8-ctf-kit-engine\environment
docker compose build
docker compose run --rm verify
```

也就是说：

- CVE：重点是能否编译出对应版本的 V8 vuln/fixed 镜像，耗时长、占用空间大。
- CTF：重点是原始题目文件是否完整、是否能被包装进统一 Harbor 目录，通常不需要重新按 CVE 流程编译 V8。
- 两者最终交付形态一致，都是 `tasks/...` 下的独立可运行任务目录。

## 校验命令

在仓库根目录执行：

```powershell
python scripts/validate_all.py
python scripts/validate_build_ready.py
python scripts/validate_ctf_build_ready.py
```

当前期望结果：

```text
Total: 45, Passed: 45
Total: 7, Ready: 7
Total: 38, Ready: 38
```
