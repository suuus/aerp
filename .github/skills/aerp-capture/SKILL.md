---
name: aerp-capture
description: Capture a structured AERP observation, assessment, approval, execution, outcome, or drift record.
---

# Capture evidence

1. Identify the subject, claim, evidence type, producer, method, environment,
   target, observation time, result, and artifacts.
2. Do not infer `passed` from the mere presence of a report. Use `observed`,
   `inconclusive`, or `error` when the result is not explicit.
3. Run `aerp new` with the collected values.
4. Add each supporting artifact with an artifact root that makes stored paths
   portable and relative.
5. Add ADRP records using repeated `--decision` arguments only when the exact
   decision records are known.
6. Run `aerp validate` and `aerp verify` before claiming completion.

Never replace a failed CLI call with a prose-only success statement.
