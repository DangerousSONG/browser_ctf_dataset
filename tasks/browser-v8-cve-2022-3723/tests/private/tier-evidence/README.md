Private round evidence and the reference payload live here.

- `reference.js` — self-contained JavaScript; not committed until it exists.
- Per-round logs must be sanitized (no secrets). Required fields: round id,
  capability, pass/fail, exit/signal, payload hash, binary hash, challenge type.

Do not copy this directory into `environment/Dockerfile`.
