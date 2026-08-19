# Browser CTF Dataset

> 浏览器漏洞利用沙箱靶场数据集。每个 CVE 对应一个独立的 Docker 项目，可单独构建、部署和验证。

## 交付说明

本仓库默认交付的是“可运行题目目录”，不是预先构建好的 Docker 镜像。

每个 `cve-*` 目录应当可以独立运行，并包含：

```text
Dockerfile
docker-compose.yml
task.yaml
README.md
run-tests.sh
poc/
exploit/
solution/
tests/
```

其中 `Dockerfile` 是构建环境的说明书；执行 `docker build` 后生成的 `browser-ctf/<cve-name>` 才是本机上的 Docker 镜像。除非特别要求，后续 CVE 只需要提交完整的可运行题目目录即可，不需要提前把每一个镜像都构建出来。

## 目录结构

```
browser_ctf_dataset/
├── cve-2018-17463/          # 独立靶场：CVE-2018-17463
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── task.yaml
│   ├── poc/
│   ├── tests/
│   ├── exploit/
│   ├── solution/
│   └── README.md
├── cve-xxxx-yyyyy/          # 后续新增的独立靶场目录
│   └── ...
├── framework/               # 共享验证框架
│   ├── verifier.py
│   ├── runner.py
│   └── schemas/
├── scripts/                   # 批量脚本
│   ├── validate_all.py
│   ├── build_all.py
│   └── init_cve.sh
├── Makefile
└── README.md
```

## 快速开始

### 准备 Docker

在 Windows 上构建前，请先启动 Docker Desktop，并确认左下角或命令行显示正在使用 Linux 引擎。

可以在 PowerShell 中检查：

```powershell
docker version
```

如果看到类似下面的错误，说明 Docker Desktop 还没有启动，或 Docker 引擎还没有就绪：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

处理方式：打开 Docker Desktop，等待引擎启动完成后重新执行构建命令。

### 构建单个靶场

以下命令会把 `cve-2018-17463` 目录构建成本机 Docker 镜像：

```powershell
cd cve-2018-17463
docker build -t browser-ctf/cve-2018-17463 .
```

构建成功后，最后通常会出现类似输出：

```text
naming to docker.io/browser-ctf/cve-2018-17463
```

也可以用下面命令检查镜像是否存在：

```powershell
docker image ls browser-ctf/cve-2018-17463
```

注意：部分浏览器漏洞环境会在 Dockerfile 中下载和编译 V8/Chromium 相关源码，首次构建可能需要较长时间。后续如果 Docker 缓存没有失效，相同步骤会明显变快。

### 验证单个靶场

在题目目录内运行测试脚本：

```powershell
cd cve-2018-17463
docker run --rm browser-ctf/cve-2018-17463
```

### 批量验证所有靶场

在仓库根目录运行结构校验：

```powershell
python scripts/validate_all.py
```

该脚本会检查所有 `cve-*` 目录是否包含必需文件，并校验 `task.yaml` 和 `Dockerfile` 的基本格式。

## 添加新靶场

```powershell
bash scripts/init_cve.sh cve-2020-6507
cd cve-2020-6507
# 编辑 Dockerfile、task.yaml、tests/...
```

新增 CVE 目录时，请确保至少满足：

- 目录名使用 `cve-年份-编号` 格式，例如 `cve-2018-17463`
- 根目录存在 `Dockerfile`、`task.yaml`、`README.md`、`run-tests.sh`
- 测试文件存在于 `tests/test_vuln.py` 和 `tests/test_func.py`
- PoC、利用脚本和修复说明分别放在 `poc/`、`exploit/`、`solution/`
- 单个目录可以独立 `docker build`

## 靶场列表

| CVE | 类型 | 难度 | 状态 |
|-----|------|------|------|
| CVE-2018-17463 | V8 JIT Type Confusion | easy | 已完成 |
