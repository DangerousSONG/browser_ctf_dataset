#!/bin/bash
# Oracle: copy the private reference payload to the Harbor submit path.
# This file must never be COPY'd into the agent image.
set -euo pipefail
REF="/tests/private/tier-evidence/reference.js"
if [[ ! -f "$REF" ]]; then
  echo "ERROR: missing private reference payload" >&2
  exit 2
fi
mkdir -p /workspace /rlenv/workspace
cp "$REF" /workspace/exploit.py
cp "$REF" /rlenv/workspace/exploit.js
chmod 644 /workspace/exploit.py /rlenv/workspace/exploit.js
