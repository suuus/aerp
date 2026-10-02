# Git-Ape evidence adapter

## Why Git-Ape is the first adapter

Git-Ape already treats `.azure/deployments/<deployment-id>/` as the execution
trace connecting requirements to deployed Azure resources. AERP formalises that
trace without moving Azure-specific concepts into the generic evidence profile.

```text
Git-Ape owns                     AERP owns
-----------------------------   --------------------------------
Azure workflow                  portable evidence semantics
deployment directory           record and bundle integrity
security and policy checks      ADRP fingerprint bindings
cost and WAF reviews            artifact digest verification
deployment and tests            interoperable exports
drift collection                honest verification levels
```

## Recognised artifacts

The adapter currently recognises:

| Artifact | Evidence type | Role |
|---|---|---|
| `requirements.json` | observation | input |
| `template.json` | execution | output |
| `parameters.json` | execution | input |
| `architecture.md` | observation | report |
| `security-analysis.md` | assessment | report |
| `security-gate.json` | assessment | report |
| `policy-assessment.md` | assessment | report |
| `policy-recommendations.json` | assessment | supporting |
| `availability-report.md` | assessment | report |
| `preflight-report.md` | assessment | report |
| `cost-estimate.json` | assessment | report |
| `waf-review.md` | assessment | report |
| `metadata.json` | execution | supporting |
| `deployment.log` | execution | log |
| `tests.json` | outcome | report |
| `error.log` | outcome | log |
| `architecture-live.md` | observation | snapshot |

Under `drift-analysis/` it recognises:

- `current-state.json`;
- `drift-report.md`;
- `drift-details.json`;
- `known-drift.json`;
- `drift-log.jsonl`.

Unknown files are not silently included. Add explicit adapter support when
their meaning and role are known.

## Result inference

The adapter uses conservative inference:

- `error.log` becomes `failed`;
- recognised structured security-gate, test, and metadata status fields may
  yield `passed`, `failed`, or `succeeded`;
- otherwise the result remains `observed`.

The existence of `security-analysis.md` is not proof that security passed.

## Command

```bash
aerp bundle-git-ape .azure/deployments/<deployment-id> \
  --identity "<producer identity>" \
  --producer-version "<git-ape version>" \
  --target "<Azure target>" \
  --decision "<ADRP record>" \
  --output .azure/deployments/<deployment-id>/evidence/bundle.json
```

Use repeated `--decision` arguments for multiple applicable decisions.

## Proposed Git-Ape integration

Git-Ape should eventually call AERP after each stage rather than only at the end:

```text
Requirements complete   → observation record
Template generated      → execution record
Security gate complete  → assessment record
Human confirms plan     → approval record
Deployment complete     → execution and outcome records
Tests complete          → outcome records
Drift check complete    → observation and drift records
```

That future integration belongs in Git-Ape. AERP remains a standalone consumer
and verifier so other deployment systems can emit the same evidence model.

## Directory recommendation

```text
.azure/deployments/<deployment-id>/
├── requirements.json
├── template.json
├── security-gate.json
├── deployment.log
├── tests.json
├── drift-analysis/
└── evidence/
    ├── bundle.json
    ├── statement.json
    └── signatures/
```

Do not place private signing keys in the deployment directory.
