# AERP — Ape Evidence Record Profile

> The durable Evidence record layer for the ISEE Framework.

[![CI](https://github.com/suuus/aerp/actions/workflows/ci.yml/badge.svg)](https://github.com/suuus/aerp/actions/workflows/ci.yml)

**AERP** is an open, machine-readable profile for binding organisational
decisions to agent actions, execution artifacts, observed outcomes, and drift.
It includes a dependency-free Python CLI, JSON Schemas, a GitHub Copilot agent,
focused skills, a Git-Ape adapter, and exports for established attestation and
compliance ecosystems. AERP is the durable **Evidence** record layer of the
**ISEE Framework: Intent → Structure → Execution → Evidence**.

Learn more about the ISEE operating framework at
[agentile.org](https://agentile.org).

```text
ADRP decision
    ↓ immutable decision fingerprint
AERP evidence records
    ↓ grouped into a portable bundle
Execution artifacts and outcomes
    ↓ re-verified by content digest
Drift, review, and reconsideration
```

AERP answers:

- What was observed or executed?
- Who or what produced the evidence?
- Which method and version were used?
- Which environment and target were involved?
- Which exact artifacts support the claim?
- Which exact ADRP record authorised or motivated the work?
- Can the record and referenced artifacts still be verified?

It deliberately does **not** decide whether a decision is authoritative,
whether a control applies, or whether an organisation is compliant.

## AERP in the ISEE Framework

```text
Intent       ADRP records decisions, authority, scope, trade-offs,
             autonomy boundaries, lifecycle, and expected evidence.
    ↓
Structure    Architecture, ownership, controls, policy, and agent boundaries
             materialise the active Intent.
    ↓
Execution    Agents and delivery systems act while retaining the exact ADRP
             fingerprints that shaped the action.
    ↓
Evidence     AERP records observations, assessments, approvals, executions,
             outcomes, artifacts, and drift.
    ↺
Review       Material Evidence challenges the original Intent through ADRP.
```

AERP does not determine whether an ADRP record is active or authoritative.
Resolve that standing with
[ADRP](https://github.com/suuus/adrp) before execution; then bind AERP evidence
to the exact canonical ADRP record and fingerprint.

See [Setting up AERP with ADRP for ISEE](docs/ISEE_INTEGRATION.md) for the
complete workflow, repository layout, agent contract, and CI pattern.

## Install with GitHub Copilot

Install the complete [ISEE plugin suite](https://github.com/suuus/isee-plugins):

```bash
copilot plugin marketplace add suuus/isee-plugins
copilot plugin install isee-suite@isee
```

To load only the AERP agent and skills:

```bash
copilot plugin install aerp@isee
```

Use the suite's `isee-setup` skill to install or diagnose the deterministic
CLIs explicitly.

## Install the CLI from a checkout

```bash
python3 -m pip install -e .
aerp --version
```

Python 3.11 or newer is required. The runtime has no third-party dependencies.

## Quick start

Create an observation:

```bash
aerp new \
  --type observation \
  --subject "production-api" \
  --claim "TLS configuration was collected" \
  --result observed \
  --summary "The scanner captured the current endpoint configuration." \
  --producer "tls-scanner" \
  --producer-version "2.4.0" \
  --identity "github-actions:example/api/.github/workflows/evidence.yml" \
  --method "tls-endpoint-scan" \
  --method-version "1" \
  --environment production \
  --target "https://api.example.com" \
  --artifact reports/tls.json \
  --artifact-root . \
  --artifact-role report \
  --output evidence/tls-observation.json
```

Bind existing evidence to a specific ADRP record:

```bash
aerp bind evidence/tls-observation.json decisions/ADR-TLS-POLICY.v1.json \
  --output evidence/tls-observation.bound.json
```

Bind Evidence to the exact ASRP Structure that governed Execution:

```bash
aerp bind-structure evidence/tls-observation.bound.json \
  structures/STR-PRODUCTION-DEPLOYMENT.v1.json \
  --output evidence/tls-observation.isee.json
```

Bundle a Git-Ape deployment trace:

```bash
aerp bundle-git-ape .azure/deployments/deploy-20261002-103000 \
  --identity "github-actions:org/repo/.github/workflows/deploy.yml" \
  --producer-version "0.8.0" \
  --target "/subscriptions/.../resourceGroups/rg-api-prod" \
  --decision decisions/ADR-SECURITY-GATE.v1.json \
  --structure structures/STR-PRODUCTION-DEPLOYMENT.v1.json \
  --output .azure/deployments/deploy-20261002-103000/evidence/bundle.json
```

Verify structure, fingerprints, and artifact bytes:

```bash
aerp validate evidence/bundle.json
aerp inspect evidence/bundle.json
aerp verify evidence/bundle.json --artifact-root .azure/deployments/deploy-20261002-103000
```

Export into established ecosystems:

```bash
aerp export-intoto evidence/bundle.json --output evidence/statement.json
aerp export-oscal evidence/bundle.json --output evidence/assessment-results.json
```

## Evidence types

| Type | Meaning |
|---|---|
| `observation` | Something was measured, retrieved, or seen |
| `assessment` | Observations were evaluated against stated criteria |
| `approval` | A human or authorised system approved a specific subject |
| `execution` | An operation was attempted with identified inputs and context |
| `outcome` | A resulting state, output, test, success, or failure was captured |
| `drift` | Later state differs from an expected or previously recorded state |

Failures, errors, warnings, and inconclusive checks are valid evidence results.
Their presence must never be rewritten as success.

## Standards relationship

AERP is a small binding profile, not a replacement for mature standards:

- **ADRP** supplies decision identity, authority, scope, lifecycle, and Intent.
- **[ASRP](https://github.com/suuus/asrp)** supplies Structure identity, gates,
  entry points, and Evidence obligations.
- **in-toto Statement** supplies a standard attestation envelope shape.
- **DSSE and Sigstore** can sign and publish exported statements.
- **SLSA provenance** remains the appropriate predicate for software build provenance.
- **OSCAL Assessment Results** can receive a compliance-oriented projection.
- **OpenTelemetry** trace and span identifiers can be carried as correlation IDs.
- **W3C PROV** concepts inform provenance relationships.
- **IETF SCITT** may provide interoperable transparency infrastructure as it matures.

Read [the interoperability guide](docs/INTEROPERABILITY.md) before integrating
AERP into signing or compliance workflows.

## Documentation

- [Standard](docs/STANDARD.md)
- [Recording and processing evidence](docs/RECORDING_EVIDENCE.md)
- [Agent integration](docs/AGENT_INTEGRATION.md)
- [ISEE integration with ADRP](docs/ISEE_INTEGRATION.md)
- [Git-Ape adapter](docs/GIT_APE.md)
- [Standards interoperability](docs/INTEROPERABILITY.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Project status

AERP `0.1.0` is an alpha implementation intended for experimentation and
interoperability design. It provides deterministic local integrity checks, but
does not by itself establish producer identity, non-repudiation, regulatory
acceptance, or legal compliance.

## License

[MIT](LICENSE)
