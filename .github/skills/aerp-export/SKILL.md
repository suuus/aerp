---
name: aerp-export
description: Export an AERP bundle as an in-toto Statement or an OSCAL Assessment Results projection.
---

# Export evidence

For an in-toto Statement:

```bash
aerp export-intoto bundle.json --output statement.json
```

The AERP bundle becomes the predicate and its artifacts become subjects. Sign
the resulting statement with established DSSE/Sigstore tooling outside AERP.

For an OSCAL Assessment Results projection:

```bash
aerp export-oscal bundle.json --output assessment-results.json
```

The OSCAL output is intentionally labelled as a mechanical projection. Validate
and enrich it with the applicable assessment plan, controls, parties, and
authorisation process before using it in a compliance package.
