# Ape Evidence Record Profile v1

## 1. Status

This document defines version 1 of the Ape Evidence Record Profile (AERP).
Normative requirements use **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**,
and **MAY** in their ordinary standards sense.

AERP is an application profile for portable evidence. It does not define a new
signature algorithm, transparency service, compliance framework, or
authorisation model.

## 2. Purpose

AERP connects four concerns that are commonly stored separately:

1. decision-bearing intent;
2. agent or system execution;
3. observations and assessments;
4. later outcomes and drift.

The central unit is an evidence record. Multiple records concerning one subject
can be transported as an evidence bundle.

## 3. Trust boundaries

```text
Decision authority       ADRP or another decision system
Evidence semantics       AERP
Artifact bytes           Referenced external files
Producer authentication  DSSE/Sigstore or another signature system
Compliance standing      Applicable governance and assessment process
```

A conforming implementation MUST NOT infer one boundary from another.

- Valid evidence does not create decision authority.
- A matching digest does not prove a trustworthy producer.
- A signed record does not prove a true claim.
- A passed assessment does not establish control applicability.
- An OSCAL export does not establish compliance.

## 4. Evidence record

An AERP record conforms to
`schemas/aerp-evidence-record-v1.schema.json` and uses
`schema_version: aerp-evidence-record/v1`.

### 4.1 Identity

`evidence_id` is a UUID identifying one evidence record. A materially changed
record MUST receive a new `evidence_id`. Existing fingerprinted records SHOULD
be treated as immutable.

### 4.2 Evidence type

`evidence_type` MUST be one of:

- `observation`;
- `assessment`;
- `approval`;
- `execution`;
- `outcome`;
- `drift`.

The type describes the semantic role of the record, not the file extension or
tool that produced it.

### 4.3 Subject

The subject identifies what the claim concerns:

- `name` is a human-meaningful identifier;
- `uri` is an optional globally or locally meaningful reference;
- `digest` optionally identifies immutable subject content.

When the subject itself is a mutable service or environment, its digest MAY be
null. Supporting snapshots SHOULD then be included as artifacts.

### 4.4 Claim

The claim records:

- the statement being supported;
- the result;
- a concise summary;
- references to explicit criteria.

Allowed results are:

- `observed`;
- `passed`;
- `failed`;
- `warning`;
- `inconclusive`;
- `error`;
- `succeeded`;
- `not-applicable`.

`observed` MUST NOT be interpreted as `passed`. `error` and `inconclusive` MUST
remain distinct from `failed`: they mean the assessment could not establish
the requested answer.

### 4.5 Producer

The producer identifies the tool, agent, workflow, or person that created the
record:

- `name`;
- `version`;
- `identity`;
- optional `invocation_id`.

The value is a claim until authenticated by an external mechanism. AERP local
validation verifies syntax and content integrity, not identity ownership.

### 4.6 Method

The method records the named procedure and version used to produce the
evidence. `parameters_digest` MAY bind a separately preserved configuration to
the method.

Reproducible assessments SHOULD preserve enough method information for another
party to understand or repeat the check.

### 4.7 Timing

`observed_at` identifies when the evidence was collected. `valid_from` and
`valid_until` MAY state an explicit applicability interval. Expiration does not
delete evidence; it changes whether that evidence is current enough for a
particular use.

### 4.8 Environment and correlation

The environment identifies a named environment and exact target. Correlation
IDs MAY include:

- deployment ID;
- workflow run ID;
- OpenTelemetry trace ID;
- OpenTelemetry span ID;
- cloud operation ID;
- change request ID.

Correlation IDs help locate related data. They do not replace artifact digests.

### 4.9 Decision bindings

Each ADRP binding contains:

- `decision_id`;
- `record_id`;
- `record_version`;
- canonical `record_fingerprint`.

Bindings MUST identify an immutable decision payload. A title, URL, or
`decision_id` alone is insufficient because it cannot distinguish versions.

A binding means “this evidence refers to this exact decision record.” It does
not mean that the decision was authoritative, active, applicable, or satisfied.

### 4.10 Policy and control references

`policy_refs` and `control_refs` contain external identifiers. A reference MUST
NOT be interpreted as proof that a policy or control applies.

### 4.11 Artifacts

Every artifact contains:

- name;
- relative path;
- media type;
- SHA-256 digest;
- role.

Paths MUST be relative so bundles remain portable. Verification MUST resolve
paths against an explicitly supplied artifact root and compare current bytes
with the stored digest.

Allowed roles are `input`, `output`, `supporting`, `report`, `log`, `snapshot`,
and `policy`.

### 4.12 Relationships

Evidence may be linked through:

- `derived_from`;
- `supersedes`;
- `revokes`.

Relationship values identify evidence records or external statements. Revoked
evidence remains part of the historical chain and MUST NOT be silently removed.

### 4.13 Integrity

The record fingerprint is:

```text
sha256(canonical JSON of the record with integrity.record_fingerprint = null)
```

Canonical JSON uses UTF-8, sorted object keys, no insignificant whitespace, and
unescaped Unicode. Arrays retain their order.

The fingerprint detects record modification. It is not a digital signature.

## 5. Evidence bundle

An AERP bundle conforms to
`schemas/aerp-evidence-bundle-v1.schema.json` and uses
`schema_version: aerp-evidence-bundle/v1`.

A bundle contains:

- bundle identity and creation time;
- bundle producer;
- common subject;
- one or more complete evidence records;
- a bundle fingerprint.

Every embedded record MUST validate independently. Evidence IDs within a bundle
MUST be unique.

The bundle fingerprint uses the same canonicalisation rule as a record, with
`integrity.bundle_fingerprint` set to null.

## 6. Verification levels

Implementations SHOULD report verification precisely:

| Level | Meaning |
|---|---|
| Structure valid | Required fields and value constraints are satisfied |
| Record integrity valid | Stored record fingerprint matches canonical content |
| Artifact integrity valid | Referenced artifact bytes match stored digests |
| Signature valid | An external signature validates cryptographically |
| Producer authenticated | Signature identity is trusted for this use |
| Claim accepted | A reviewer accepts the evidence and method |
| Compliance standing | Applicable governance concludes requirements are met |

Lower levels MUST NOT be described as higher levels.

## 7. Failure handling

Implementations MUST:

- fail on malformed records;
- fail on fingerprint mismatch;
- fail artifact verification on missing or changed files;
- preserve explicit failure and error results;
- avoid success-shaped defaults;
- avoid silently dropping unknown or unsupported evidence.

## 8. External formats

AERP bundles MAY be exported as in-toto Statements. AERP itself does not sign
the statement. DSSE, Sigstore, or another established mechanism SHOULD be used
when authenticated attestations are required.

AERP records MAY be projected into OSCAL Assessment Results. Such exports MUST
state that applicability, reviewed controls, assessment plans, parties, and
compliance standing require completion by the receiving governance process.

## 9. Privacy and security

Evidence often contains sensitive operational information. Producers SHOULD:

- minimise secrets and personal data;
- use stable identities rather than credentials;
- redact sensitive command output before capture;
- separate restricted artifacts from public metadata;
- define retention and access policies;
- sign and timestamp high-consequence evidence;
- protect artifact roots against unauthorised modification.

A digest can reveal whether a guessed document matches. It is not encryption.
