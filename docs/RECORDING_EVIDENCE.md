# Recording and processing evidence

## Why evidence needs structure

Agent systems often produce reports, logs, screenshots, test output, and
approval messages. Merely retaining those files does not answer:

- which decision led to the action;
- whether the report concerns the exact deployed artifact;
- what method produced the result;
- who or what ran the method;
- whether the file changed afterward;
- whether an observation was treated as a pass without justification;
- whether later drift invalidated the original conclusion.

AERP turns those loose artifacts into explicit, verifiable records.

## The semantic ladder

Keep these statements separate:

```text
Observation
  "The endpoint negotiated TLS 1.2."

Assessment
  "TLS 1.2 satisfies criterion SECURITY-TLS-01."

Compliance conclusion
  "The applicable transport-security control is satisfied."

Decision
  "The organisation accepts this implementation for production."
```

Each step adds interpretation or authority. An agent MUST NOT skip steps merely
because a tool returned green output.

## Choosing an evidence type

### Observation

Use when a tool, person, or agent measures or retrieves something without
evaluating it against a criterion.

Examples:

- Azure resource configuration snapshot;
- HTTP response;
- package inventory;
- cost API response;
- current policy assignment.

### Assessment

Use when evidence is evaluated against explicit criteria.

Examples:

- security gate result;
- architecture review;
- policy evaluation;
- control test;
- cost threshold check.

Include criteria references wherever possible.

### Approval

Use when an authorised actor approves a fingerprinted subject or plan. Preserve
what was approved, by whom, when, and in which invocation. Approval evidence
must not contain passwords, tokens, or session credentials.

### Execution

Use when a tool or agent attempts an operation. Capture inputs, target,
invocation identity, outputs, and errors. “Execution” does not imply success.

### Outcome

Use for resulting state and post-execution tests. A successful deployment and a
healthy service are separate claims and often require separate records.

### Drift

Use when later observation differs from an expected or previously recorded
state. Accepted drift should be accompanied by approval or a new decision, not
silently removed from reports.

## Authoring workflow

### 1. Identify the claim

Write one claim that can be supported or challenged:

> The production API passed the repository's transport-security test suite.

Avoid vague claims:

> Security is good.

### 2. Identify the subject

Name the exact service, deployment, artifact, plan, or environment. Add a URI
or digest when one exists.

### 3. Name the producer and method

Record the exact tool and method version. “Copilot checked it” is insufficient
when the underlying scanner or script is known.

### 4. Preserve artifacts

Store relevant machine output and calculate its digest. Do not rely only on a
human-readable summary when structured output exists.

### 5. Bind applicable decisions

Bind evidence to an exact ADRP record:

```bash
aerp bind evidence.json ADR-SECURITY-GATE.v1.json --output evidence.bound.json
```

Binding is appropriate when the decision genuinely motivated, required, or
authorised the action. Do not attach every organisational decision to every
piece of evidence.

### 6. Verify

```bash
aerp validate evidence.bound.json
aerp verify evidence.bound.json --artifact-root .
```

If artifact verification fails, determine whether:

- the artifact changed;
- the wrong root was supplied;
- the file was moved;
- the evidence package is incomplete.

Do not update the stored digest merely to make verification pass. Create a new
record describing the new artifact.

## Git-Ape workflow

Git-Ape already stores a deployment trace under
`.azure/deployments/<deployment-id>/`. AERP converts recognised artifacts into
individual records inside one bundle:

```bash
aerp bundle-git-ape .azure/deployments/deploy-20261002-103000 \
  --identity "github-actions:org/repo/.github/workflows/deploy.yml" \
  --producer-version "0.8.0" \
  --target "/subscriptions/000.../resourceGroups/rg-prod" \
  --decision decisions/ADR-SECURITY-GATE.v1.json \
  --output .azure/deployments/deploy-20261002-103000/evidence/bundle.json
```

The adapter recognises documented requirements, template, security, policy,
cost, WAF, preflight, deployment, test, live-state, and drift artifacts.

The adapter does not claim to understand every report's internal semantics.
When a result cannot safely be inferred, it records `observed`.

## Signing

AERP fingerprints provide local content integrity. For authenticated
attestations:

1. export an in-toto Statement;
2. wrap or sign it using DSSE/Sigstore tooling;
3. verify the signature and identity under an explicit trust policy;
4. preserve the signature or transparency-log reference next to the bundle.

Example export:

```bash
aerp export-intoto bundle.json --output statement.json
```

AERP intentionally does not implement private-key handling.

## Compliance export

```bash
aerp export-oscal bundle.json --output assessment-results.json
```

This creates observations suitable for further OSCAL processing. Assessments
with explicit control references and `passed` or `failed` results are also
projected as findings. Before official use, the receiving process must supply
or validate:

- assessment plan;
- applicable control selections;
- parties and roles;
- responsible assessment organisation;
- finding status semantics;
- risks and remediation;
- framework-specific extensions;
- package validation.

## Evidence lifecycle

Evidence should not be edited in place after fingerprinting. Use relationships:

- `supersedes` for a newer evidence record replacing an older conclusion;
- `revokes` when evidence should no longer be relied on;
- `derived_from` when one record was produced from other evidence.

Old evidence remains useful history even when it is stale or revoked.

## Human review checklist

- Is the claim specific?
- Is the evidence type accurate?
- Is the result explicit rather than inferred?
- Is the producer identifiable?
- Is the method reproducible or at least understandable?
- Is the target exact?
- Are artifact paths portable?
- Do artifact digests verify?
- Are decision bindings exact and relevant?
- Is any validity period justified?
- Are secrets and personal data excluded?
- Does the wording avoid overstating compliance or authority?
