#!/bin/bash
# Public Harbor verifier entry. Reads /workspace/exploit.py.
# Private logic lives in tests/private/ (copied here by Harbor at verify time,
# never baked into the agent image).
set -u
mkdir -p /logs/verifier /rlenv/workspace

SUBMIT="${HARBOR_SUBMIT:-/workspace/exploit.py}"
HARNESS="/tests/private/harness/run_submission.py"

if [[ ! -f "$HARNESS" ]]; then
  echo "ERROR: private harness missing (infra)" >&2
  echo "ERROR" > /logs/verifier/status.txt
  echo "0" > /logs/verifier/reward.txt
  exit 2
fi

python3 "$HARNESS" "$SUBMIT"
rc=$?

case "$rc" in
  0)
    echo "PASS" > /logs/verifier/status.txt
    echo "1" > /logs/verifier/reward.txt
    ;;
  1)
    echo "FAIL" > /logs/verifier/status.txt
    echo "0" > /logs/verifier/reward.txt
    ;;
  *)
    echo "ERROR" > /logs/verifier/status.txt
    echo "0" > /logs/verifier/reward.txt
    rc=2
    ;;
esac

exit "$rc"
