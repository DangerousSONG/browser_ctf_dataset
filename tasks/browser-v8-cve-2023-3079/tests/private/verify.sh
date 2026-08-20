#!/bin/bash
# Private: vuln vs fixed, 3-round contract. Infra failures must be ERROR (2),
# not FAIL (1).
set -u
exec python3 /tests/private/harness/run_submission.py \
  --mode verify \
  --contract /tests/private/capability_contract.json \
  "${HARBOR_SUBMIT:-/workspace/exploit.py}"
