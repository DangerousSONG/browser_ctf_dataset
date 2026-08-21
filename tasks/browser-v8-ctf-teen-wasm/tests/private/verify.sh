#!/bin/bash
set -u
exec python3 /tests/private/harness/run_submission.py "${HARBOR_SUBMIT:-/workspace/exploit.py}"
