# Browser CTF Dataset

面向浏览器 V8 漏洞复现的 CTF / Harbor 任务目录集合。

本仓库的交付目标不是提交已经编译好的大体积 Docker 镜像，而是提交每个
CVE / CTF 题目的可运行任务目录。每个任务目录都包含 Dockerfile、
docker-compose 配置、任务元信息、测试入口和私有验证目录，方便后续在本地、
CI 或专门的 Linux amd64 构建机上编译与验证。

当前状态：

- 7 个任务目录已经全部通过结构校验和 build-ready 校验。
- `CVE-2024-5830` 已经额外完成本机 Docker 镜像编译和 compose 启动验证。

已经完整构建并验证过镜像的样例：

- `tasks/browser-v8-cve-2024-5830`
- 底层 V8 镜像：`cve-2024-5830:latest`
- Harbor 包装镜像：`browser-v8-cve-2024-5830:latest`

## 仓库结构

```text
browser_ctf_dataset/
├── candidates/                     # CVE 候选材料和筛选记录
├── scripts/                        # 同步、生成、bootstrap、校验、构建脚本
├── tasks/                          # 最终交付的 Harbor 任务目录
│   └── browser-v8-cve-2024-5830/
│       ├── task.toml
│       ├── instruction.md
│       ├── environment/
│       │   ├── Dockerfile
│       │   ├── docker-compose.yaml
│       │   ├── task.yaml
│       │   └── task-deps/
│       └── tests/
│           ├── test.sh
│           └── private/
├── templates/harbor/               # 统一任务模板
├── third_party/exploitbench/        # 上游 ExploitBench / bench-v8
├── pins.toml                        # 固定版本和依赖来源
└── README.md
```

每个 CVE 后续都应该是一个独立目录：

```text
tasks/browser-v8-<cve-id>/
```

例如：

```text
tasks/browser-v8-cve-2024-5830/
tasks/browser-v8-cve-2024-8904/
tasks/browser-v8-cve-2023-3079/
```

## 镜像存在哪里

Docker 镜像不会作为普通文件出现在项目目录里。

构建成功后，镜像会进入 Docker Desktop 的本地镜像库。可以用下面命令查看：

```powershell
docker images cve-2024-5830
docker images cve-2024-5830-dev
docker images browser-v8-cve-2024-5830
```

本机已经验证过的结果示例：

```text
IMAGE                      ID             DISK USAGE   CONTENT SIZE
cve-2024-5830-dev:latest   aa4405290577       94.6GB         22.6GB
```

说明：

- `cve-2024-5830-dev:latest` 是实际编译出的 bench-v8 底层镜像。
- `cve-2024-5830:latest` 是给 compose 默认配置使用的本地别名。
- `browser-v8-cve-2024-5830:latest` 是 Harbor 包装层镜像。

如果只有 `cve-2024-5830-dev:latest`，可以补一个别名：

```powershell
docker tag cve-2024-5830-dev:latest cve-2024-5830:latest
```

这个命令不会重新编译，只是给同一个镜像增加一个名字。

## 环境要求

推荐环境：

- Windows + Docker Desktop，且 Docker Desktop 已启动 Linux engine
- 或 Ubuntu / Linux amd64 构建机
- 至少 100GB 可用磁盘空间
- 建议 16GB 以上内存
- 构建一个完整 V8 样例可能需要 1 到 3 小时，取决于机器和网络

本机实际验证数据：

- `CVE-2024-5830` 完整构建耗时约 2 小时 51 分钟
- Docker 显示镜像磁盘占用约 94.6GB
- 构建日志显示内容大小约 22.6GB

## 快速校验任务目录

结构校验不会编译 V8，速度较快。

在仓库根目录执行：

```powershell
python scripts/validate_all.py
```

期望结果：

```text
Total: 7, Passed: 7
```

再检查哪些任务已经具备真实构建材料：

```powershell
python scripts/validate_build_ready.py
```

当前 build-ready 状态：

```text
[READY] browser-v8-cve-2018-17463
[READY] browser-v8-cve-2022-3723
[READY] browser-v8-cve-2023-2033
[READY] browser-v8-cve-2023-3079
[READY] browser-v8-cve-2023-4069
[READY] browser-v8-cve-2024-5830
[READY] browser-v8-cve-2024-8904

Total: 7, Ready: 7
```

如果后续新增任务显示 `PENDING_BOOTSTRAP`，表示目录结构已经生成，但还没有补齐真实的
V8 revision pair 和 inner Dockerfile，不能保证直接编译。

## 构建一个完整样例

下面以 `CVE-2024-5830` 为例。

在仓库根目录执行：

```powershell
python scripts/build_inner.py CVE-2024-5830 --dev --no-export
```

说明：

- `--dev`：生成开发验证用镜像，速度相对更快。
- `--no-export`：不导出压缩包，只保留 Docker 本地镜像。
- 输出镜像通常是 `cve-2024-5830-dev:latest`。

构建成功后，给它补一个 compose 默认会使用的别名：

```powershell
docker tag cve-2024-5830-dev:latest cve-2024-5830:latest
```

确认镜像存在：

```powershell
docker images cve-2024-5830
docker images cve-2024-5830-dev
```

## 用 docker compose 构建包装层

进入样例任务的环境目录：

```powershell
cd D:\Code\browser_ctf_dataset\tasks\browser-v8-cve-2024-5830\environment
```

构建 Harbor 包装镜像：

```powershell
docker compose build
```

成功后会得到：

```text
browser-v8-cve-2024-5830:latest
```

确认包装镜像存在：

```powershell
docker images browser-v8-cve-2024-5830
```

## 证明环境可以运行

### 证明 1：底层镜像里的 V8 可以启动

```powershell
docker run --rm --entrypoint /bin/bash cve-2024-5830 -lc "find /rlenv/binaries -maxdepth 3 -type f -name d8 | sort"
```

期望能看到 vuln / fixed 两套 V8 产物，例如：

```text
/rlenv/binaries/fixed/coverage/d8
/rlenv/binaries/fixed/debug-asan/d8
/rlenv/binaries/fixed/debug/d8
/rlenv/binaries/fixed/release-asan/d8
/rlenv/binaries/fixed/release/d8
/rlenv/binaries/vuln/coverage/d8
/rlenv/binaries/vuln/debug-asan/d8
/rlenv/binaries/vuln/debug/d8
/rlenv/binaries/vuln/release-asan/d8
/rlenv/binaries/vuln/release/d8
```

再执行一个最小 JS：

```powershell
docker run --rm --entrypoint /bin/bash cve-2024-5830 -lc "/rlenv/binaries/vuln/release/d8 -e 'print(1+1)'"
```

期望输出：

```text
2
```

### 证明 2：docker compose 可以启动任务环境

在 `tasks/browser-v8-cve-2024-5830/environment` 目录执行：

```powershell
docker compose run --rm --entrypoint /bin/bash verify -lc "/rlenv/binaries/vuln/release/d8 -e 'print(1+1)'"
```

期望输出：

```text
2
```

也可以同时验证 fixed 版本：

```powershell
docker compose run --rm --entrypoint /bin/bash verify -lc "/rlenv/binaries/vuln/release/d8 -e 'print(1+1)'; /rlenv/binaries/fixed/release/d8 -e 'print(3+4)'"
```

本机已经验证过的输出：

```text
2
7
```

这能证明：

- Docker 镜像能启动。
- 镜像里包含真实编译出的 V8。
- vuln / fixed 两套二进制都存在。
- docker compose 包装层可以正常运行。

## 完整漏洞验证怎么跑

完整验证入口是：

```powershell
docker compose run --rm verify
```

这个命令会读取：

```text
/workspace/exploit.py
```

也就是宿主机上的：

```text
tasks/browser-v8-cve-2024-5830/workspace/exploit.py
```

如果只是验证环境是否能启动，不需要准备 `exploit.py`，用上一节的 `d8 -e`
命令即可。

如果要验证一个真实解题脚本，需要先创建 workspace 并放入提交文件：

```powershell
cd D:\Code\browser_ctf_dataset\tasks\browser-v8-cve-2024-5830
mkdir workspace
notepad workspace\exploit.py
```

然后运行：

```powershell
cd D:\Code\browser_ctf_dataset\tasks\browser-v8-cve-2024-5830\environment
docker compose run --rm verify
```

结果含义：

- 退出码 `0`：验证通过。
- 退出码 `1`：验证失败，通常是 exploit 不满足题目要求。
- 退出码 `2`：环境或验证器错误。

验证结果会写入 Docker volume 中的日志目录，也会在命令行输出关键信息。

## 生成和补齐其他 CVE

生成 Harbor 任务目录：

```powershell
python scripts/wrap_harbor_task.py CVE-2024-5830
```

批量生成候选任务：

```powershell
python scripts/generate_all.py
```

同步上游 ExploitBench：

```powershell
python scripts/sync_upstream.py
```

在 Windows 上执行 Linux-only bootstrap：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_with_docker.ps1 CVE-2024-5830
```

bootstrap 完成后重新包装任务目录：

```powershell
python scripts/wrap_harbor_task.py CVE-2024-5830 --force
```

检查是否已经可构建：

```powershell
python scripts/validate_build_ready.py
```

只有显示 `[READY]` 的任务，才表示已经补齐真实构建材料。

## 常见问题

### Docker 提示找不到 daemon

错误类似：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

处理方式：

1. 打开 Docker Desktop。
2. 等待左下角显示 Docker engine running。
3. 确认使用的是 Linux containers。
4. 重新执行 Docker 命令。

### docker compose build 找不到 cve-2024-5830

错误类似：

```text
pull access denied for cve-2024-5830
```

说明本地没有默认镜像名。可以给 dev 镜像添加别名：

```powershell
docker tag cve-2024-5830-dev:latest cve-2024-5830:latest
```

然后重新运行：

```powershell
docker compose build
```

### 磁盘空间不够

一个完整 V8 样例可能占用几十 GB 到接近 100GB。查看镜像：

```powershell
docker images
```

清理不再使用的构建缓存：

```powershell
docker builder prune
```

清理不再使用的镜像和容器：

```powershell
docker system prune
```

注意：清理命令会删除未使用的 Docker 资源，执行前确认没有需要保留的镜像。

## 交付说明

领导要求的“每一个 CVE 的可运行题目目录”，对应本仓库里的：

```text
tasks/browser-v8-<cve-id>/
```

对每个任务目录，至少需要保证：

- 结构校验通过：`python scripts/validate_all.py`
- 构建材料就绪：`python scripts/validate_build_ready.py`
- 底层镜像可以构建：`python scripts/build_inner.py <CVE> --dev --no-export`
- compose 包装层可启动：`docker compose build`
- V8 二进制可执行：`docker compose run --rm --entrypoint /bin/bash verify -lc "/rlenv/binaries/vuln/release/d8 -e 'print(1+1)'"`

当前 7 个任务都已经 build-ready；其中已经实际完整编译并启动验证过镜像的样例是
`CVE-2024-5830`。

## 版本固定

固定版本见：

```text
pins.toml
```

本仓库复用 ExploitBench / bench-v8 的构建流程，不重新手写 V8 fetch 流程。
这样可以减少每个 CVE 都重复踩 `gclient`、`depot_tools`、V8 版本漂移等问题。
