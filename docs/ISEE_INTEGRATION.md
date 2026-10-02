# AERP and ADRP in the ISEE Framework

## Purpose

The **ISEE Framework** governs agentic work as a closed loop:

```text
Intent → Structure → Execution → Evidence
```

AERP provides the durable Evidence record layer. ADRP provides the complementary
Intent record layer.

| ISEE layer | Question | Record or system |
|---|---|---|
| Intent | What was decided, by whom, for which scope, and with what autonomy? | ADRP |
| Structure | How is that Intent materialised in architecture, ownership, policy, controls, and workflows? | Referenced implementation artifacts |
| Execution | What action did an agent, workflow, platform, or person perform? | Git-Ape or another execution system |
| Evidence | What was observed, assessed, approved, executed, produced, or found to have drifted? | AERP |

The boundary matters:

- ADRP establishes decision standing and applicability.
- AERP binds Evidence to exact ADRP record fingerprints.
- AERP does not make an ADRP record active.
- Evidence can trigger ADRP review but cannot rewrite Intent.

The ADRP repository contains the corresponding
[Intent-first setup guide](https://github.com/suuus/adrp/blob/main/docs/ISEE_INTEGRATION.md).

## Install both tools

From sibling checkouts:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ../adrp -e ../aerp

adrp --version
aerp --version
```

Neither CLI depends on the other at runtime. The workflow or agent passes
canonical records between them explicitly.

## Recommended layout

```text
.
├── .github/
│   └── decisions/
│       └── ADR-SECURITY-GATE/
│           └── v001.json
├── architecture/
│   ├── policies/
│   └── diagrams/
├── evidence/
│   ├── observations/
│   ├── assessments/
│   └── outcomes/
└── .azure/
    └── deployments/
        └── <deployment-id>/
            ├── requirements.json
            ├── template.json
            ├── security-gate.json
            ├── tests.json
            └── evidence/
                └── bundle.json
```

## Setup workflow

### 1. Resolve Intent with ADRP

```bash
adrp verify-set .github/decisions

adrp resolve .github/decisions \
  --scope "production deployments" \
  --as-of "2026-10-02T12:00:00Z"
```

Retain each active record's:

- canonical file;
- `decision_id`;
- `record_id`;
- `record_version`;
- `record_fingerprint`.

AERP accepts the canonical record file and independently calculates the ADRP
payload fingerprint. The execution system should carry the same identity in its
plan, approval, and trace.

### 2. Preserve Structure references

ADRP implementation references should point to the architecture, policy,
control, workflow, and agent artifacts used to materialise Intent. AERP can
capture those files as `input`, `policy`, or `supporting` artifacts when they
matter to an evidence claim.

### 3. Capture Evidence during Execution

Create a record with an ADRP binding:

```bash
aerp new \
  --type assessment \
  --subject "deployment deploy-20261002-103000" \
  --claim "The required security gate passed" \
  --result passed \
  --summary "No blocking security findings remained." \
  --producer "git-ape-security-gate" \
  --producer-version "1.0.0" \
  --identity "github-actions:org/repo/.github/workflows/deploy.yml" \
  --method "security-gate" \
  --method-version "1" \
  --environment production \
  --target "/subscriptions/.../resourceGroups/rg-api-prod" \
  --decision .github/decisions/ADR-SECURITY-GATE/v001.json \
  --artifact .azure/deployments/deploy-20261002-103000/security-gate.json \
  --artifact-root . \
  --artifact-role report \
  --control-ref "SECURITY-GATE-01" \
  --correlation "deployment_id=deploy-20261002-103000" \
  --output evidence/assessments/security-gate.json
```

The record now contains the exact ADRP decision identity and fingerprint.

### 4. Bind existing Evidence

If evidence was collected before the ADRP file was available:

```bash
aerp bind \
  evidence/assessments/security-gate.unbound.json \
  .github/decisions/ADR-SECURITY-GATE/v001.json \
  --output evidence/assessments/security-gate.json
```

`aerp bind` creates a new immutable output rather than overwriting the original.

### 5. Bundle an execution trace

For Git-Ape:

```bash
aerp bundle-git-ape .azure/deployments/deploy-20261002-103000 \
  --identity "github-actions:org/repo/.github/workflows/deploy.yml" \
  --producer-version "0.8.0" \
  --target "/subscriptions/.../resourceGroups/rg-api-prod" \
  --decision .github/decisions/ADR-SECURITY-GATE/v001.json \
  --output .azure/deployments/deploy-20261002-103000/evidence/bundle.json
```

The adapter captures recognised requirements, architecture, security, policy,
cost, preflight, deployment, test, live-state, and drift artifacts. Unknown
files are not silently claimed as evidence.

### 6. Verify Evidence and artifacts

```bash
aerp validate evidence/assessments/security-gate.json
aerp inspect evidence/assessments/security-gate.json
aerp verify evidence/assessments/security-gate.json --artifact-root .

aerp verify \
  .azure/deployments/deploy-20261002-103000/evidence/bundle.json \
  --artifact-root .azure/deployments/deploy-20261002-103000
```

This verifies AERP structure, fingerprints, and referenced artifact bytes. It
does not authenticate the producer. Use DSSE/Sigstore or another established
system when authenticated attestations are required.

### 7. Close Evidence back into Intent

Compare verified AERP records with:

- ADRP expected evidence references;
- decision assumptions and accepted risks;
- lifecycle review and expiry dates;
- event-based drift triggers;
- autonomy and escalation boundaries.

Route the decision back to review when Evidence is missing, failed,
inconclusive, expired, materially different from the selected implementation,
or shows relevant drift.

Do not edit the ratified ADRP record or the fingerprinted AERP record. Create
new versions and relationships that preserve history.

## Agent handoff

An ISEE-aware orchestration should pass a small immutable manifest:

```json
{
  "intent": [
    {
      "decision_id": "ADR-SECURITY-GATE",
      "record_id": "849535a2-fb8d-4a59-a9ea-d01ff9b7b460",
      "record_version": 1,
      "record_fingerprint": "sha256:...",
      "canonical_path": ".github/decisions/ADR-SECURITY-GATE/v001.json"
    }
  ],
  "execution_id": "deploy-20261002-103000",
  "target": "/subscriptions/.../resourceGroups/rg-api-prod"
}
```

The Structure and Execution stages may enrich this manifest but must not replace
the selected Intent record without a new resolution and approval.

## CI baseline

```yaml
- name: Verify ISEE Intent
  run: adrp verify-set .github/decisions

- name: Verify ISEE Evidence
  run: |
    aerp validate .azure/deployments/${DEPLOYMENT_ID}/evidence/bundle.json
    aerp verify \
      .azure/deployments/${DEPLOYMENT_ID}/evidence/bundle.json \
      --artifact-root .azure/deployments/${DEPLOYMENT_ID}
```

Add separate policy checks for:

- ADRP scope resolution;
- autonomy evaluation;
- required evidence presence;
- DSSE/Sigstore verification;
- producer identity;
- control applicability;
- retention and access.

## Invariants

- AERP binding does not create ADRP standing.
- ADRP standing does not prove execution.
- Structure references do not prove implementation.
- AERP fingerprints do not authenticate producers.
- Signed evidence does not automatically prove a true claim.
- Passed evidence does not automatically establish compliance.
- Negative and inconclusive evidence remains visible.
- Evidence closes the ISEE loop through explicit Intent review.
