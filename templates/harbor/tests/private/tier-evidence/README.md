# Private evidence for {cve}

Direction: {direction}
Recommended role: {recommended_as}
Chrome fixed version: {chrome_fixed_version}
Grader range: {grader_range}
Declared tier goal: {declared_tier_goal}
Minimum accepted tier: {min_accepted_tier}
Eval flags: {eval_flags_json}

Notes:

{notes}

Sources:

{sources_markdown}

## Files

- `reference.js` — self-contained JavaScript; not committed until it exists.
- Per-round logs must be sanitized (no secrets). Required fields: round id,
  capability, pass/fail, exit/signal, payload hash, binary hash, challenge type.

Do not copy this directory into `environment/Dockerfile`.
