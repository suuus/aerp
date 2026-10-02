# Standards interoperability

## Design principle

AERP fills one narrow gap: binding decision-bearing intent to heterogeneous
execution and outcome evidence. It reuses established ecosystems rather than
reimplementing their strongest capabilities.

## ADRP

ADRP records why a choice was made, who may authorise it, where it applies, its
lifecycle, and its autonomy implications. AERP stores the immutable ADRP record
fingerprint alongside evidence.

The link is deliberately one-way:

```text
AERP evidence → exact ADRP record
```

An evidence record does not change ADRP standing. Material evidence may prompt
a new ADRP review, supersession, or revocation through the ADRP process.

## in-toto

`aerp export-intoto` produces an in-toto Statement:

- AERP artifacts become Statement subjects.
- The complete AERP bundle becomes the predicate.
- The predicate type is
  `https://aerp.dev/predicate/evidence-bundle/v1`.

This provides a standard attestation shape while retaining AERP semantics.
AERP does not claim that its predicate is an in-toto or SLSA standard.

## DSSE and Sigstore

DSSE can wrap signed statements. Sigstore can provide keyless identities and
transparency services. AERP intentionally excludes private-key management,
certificate issuance, and transparency-log implementation.

Recommended flow:

```text
AERP bundle
  → in-toto Statement
  → DSSE/Sigstore signing
  → signature and identity verification
  → optional transparency publication
```

Trust policy remains deployment-specific. A valid signature proves control of
an identity or key under that system, not truth of the evidence claim.

## SLSA

Use SLSA provenance for software build provenance. Do not replace a
well-supported SLSA predicate with AERP.

AERP can reference a SLSA attestation as a supporting artifact and bind it to
the organisational decision that required a particular build process.

## OSCAL

`aerp export-oscal` projects records into OSCAL Assessment Results observations.
It only creates findings for assessments that have an explicit `control_refs`
entry and a `passed` or `failed` result. The exporter cannot infer:

- the authoritative assessment plan;
- applicable control selections;
- assessment parties and roles;
- risk acceptance;
- framework extensions;
- formal compliance standing.

Those must be supplied and validated by the compliance process. The generated
file is a starting point for integration, not a submission-ready package.

## W3C PROV

AERP's producer, subject, activity-like execution, and `derived_from`
relationships align conceptually with W3C PROV entities, activities, agents,
and derivations. Version 1 does not define a complete PROV serialisation.

## OpenTelemetry

Trace IDs and span IDs can be placed in `environment.correlation_ids`. This
lets operators locate distributed traces without treating mutable telemetry
storage as the evidence record itself.

## IETF SCITT

SCITT addresses interoperable transparency and trust infrastructure for signed
statements. AERP statements may become suitable SCITT payloads, but AERP v1
does not depend on draft protocol details or claim SCITT conformance.

## OSCAL versus AERP

| Concern | AERP | OSCAL |
|---|---|---|
| Generic execution evidence | Primary | Can be represented as observations |
| ADRP decision fingerprint | Native | Extension/property |
| Artifact digest verification | Native | Representable |
| Control catalog and profile | Reference only | Primary |
| Assessment plan | Out of scope | Primary |
| Assessment results | Basic evidence semantics | Rich compliance model |
| Regulatory package | Out of scope | Intended use |

## Interoperability rule

Exports MUST preserve uncertainty and failure. A source `inconclusive` or
`error` result must never become a passing finding merely because the target
format expects assessment data.
