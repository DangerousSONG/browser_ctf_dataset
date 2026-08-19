#!/bin/bash
# 初始化新 CVE 靶场目录
set -e

CVE_ID=$1

if [ -z "$CVE_ID" ]; then
    echo "Usage: $0 <cve-id>"
    echo "Example: $0 cve-2020-6507"
    exit 1
fi

if [ -d "$CVE_ID" ]; then
    echo "[ERROR] Directory $CVE_ID already exists"
    exit 1
fi

mkdir -p "$CVE_ID"/{poc,exploit,tests,solution}

cat > "$CVE_ID/task.yaml" <<'EOF'
instruction: |-
  描述漏洞场景和利用目标...
difficulty: medium
category: security
tags:
  - v8
  - jit
parser_name: pytest
run_tests_in_same_shell: false
EOF

cat > "$CVE_ID/Dockerfile" <<'EOF'
FROM ubuntu:20.04
# TODO: 添加漏洞环境构建逻辑
EOF

cat > "$CVE_ID/docker-compose.yml" <<'EOF'
version: '3.8'
services:
  app:
    build: .
    image: browser-ctf/REPLACE_ME
    container_name: REPLACE_ME
    mem_limit: 512m
    cpus: 1.0
    read_only: true
    cap_drop:
      - ALL
EOF

cat > "$CVE_ID/run-tests.sh" <<'EOF'
#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m pytest tests/ -v
EOF
chmod +x "$CVE_ID/run-tests.sh"

cat > "$CVE_ID/tests/test_func.py" <<'EOF'
import subprocess

def test_d8_exists():
    result = subprocess.run(["d8", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "d8 not found"

def test_basic_js():
    result = subprocess.run(["d8", "-e", "print(1+1)"], capture_output=True, text=True)
    assert "2" in result.stdout
EOF

cat > "$CVE_ID/tests/test_vuln.py" <<'EOF'
import subprocess

def test_exploit_success():
    # TODO: 验证漏洞可被利用
    pass
EOF

cat > "$CVE_ID/tests/conftest.py" <<'EOF'
D8_PATH = "/usr/local/bin/d8"
FLAG_PATH = "/opt/flag.txt"
EOF

cat > "$CVE_ID/README.md" <<EOF
# $CVE_ID

## 基本信息

| 属性 | 值 |
|------|-----|
| CVE | $CVE_ID |
| 类型 | TODO |
| 难度 | medium |

## 快速开始

\`\`\`bash
docker build -t browser-ctf/$CVE_ID .
docker run --rm browser-ctf/$CVE_ID
\`\`\`
EOF

echo "[+] Created CVE task: $CVE_ID/"
