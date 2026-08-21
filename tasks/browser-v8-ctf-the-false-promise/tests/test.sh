#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/private/harness/run_submission.py "${HARBOR_SUBMIT:-/workspace/exploit.py}"
