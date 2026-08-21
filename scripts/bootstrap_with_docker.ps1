param(
    [Parameter(Mandatory = $true)]
    [string]$Cve
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Bench = "/src/third_party/exploitbench/benchmarks/bench-v8"

Write-Host "[1/3] Build Linux amd64 MCP server"
docker run --rm `
    -v "${Root}:/src" `
    -w "$Bench/mcp-server" `
    -e CGO_ENABLED=0 `
    -e GOOS=linux `
    -e GOARCH=amd64 `
    golang:1.25-bookworm `
    go build -o server ./cmd/server/

Write-Host "[2/3] Bootstrap $Cve in Linux"
docker run --rm `
    -v "${Root}:/src" `
    -w /src `
    python:3.12-bookworm `
    bash -lc "pip install -q -r third_party/exploitbench/benchmarks/bench-v8/requirements.txt && python scripts/bootstrap_bug.py $Cve --force && python scripts/wrap_harbor_task.py $Cve --force"

Write-Host "[3/3] Validate generated package"
docker run --rm `
    -v "${Root}:/src" `
    -w /src `
    python:3.12-bookworm `
    python scripts/validate_task.py "tasks/browser-v8-$($Cve.ToLower())"
