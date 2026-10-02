# Agent integration

## Dependency direction

Within ISEE, the agent operates the Evidence boundary:

```text
Intent             Structure            Execution            Evidence
ADRP resolve  →     referenced      →    consuming agent  →    AERP capture
and fingerprint     architecture          or system             and verify
```

The AERP agent must receive exact ADRP files or fingerprints from the Intent
stage. It must not infer current decision standing from an evidence binding.

```text
AERP Agent
    ↓ orchestrates semantic workflows
AERP Skills
    ↓ call deterministic operations
aerp CLI
    ↓ reads and writes
AERP records, bundles, and exports
```

The CLI never calls an LLM or skill. This preserves deterministic validation
and makes the same evidence checks available in local development, CI, and
non-agent systems.

## Agent processing model

Agents should use:

```text
Recognise → Collect → Classify → Bind → Verify → Explain
```

### Recognise

Determine whether the material is evidence or merely an assertion, plan, or
instruction. Future intent belongs in ADRP; past or current observations belong
in AERP.

### Collect

Collect the subject, producer, method, target, time, artifacts, and explicit
result. Never invent missing evidence.

### Classify

Choose the narrowest correct evidence type. In particular:

- tool output without criteria is normally an observation;
- evaluation against criteria is an assessment;
- a deployment attempt is execution;
- a later health check is outcome;
- a human confirmation is approval only when the approved subject is clear.

### Bind

Bind to exact ADRP records by fingerprint. The agent should resolve active ADRP
decisions before execution, then pass those exact files to AERP capture or
bundling.

### Verify

Run CLI validation and artifact verification. Tool failure blocks claims that
the evidence is valid or verified.

### Explain

Report verification level precisely. Prefer:

> The bundle structure, fingerprints, and 12 artifact digests verify locally.
> It is not signed.

Avoid:

> The deployment is certified compliant.

## Stable CLI contracts

Commands emit JSON on stdout and errors on stderr. Success returns exit code 0;
profile or verification errors return exit code 2.

Key commands:

```bash
aerp validate <record-or-bundle>
aerp fingerprint <record-or-bundle>
aerp inspect <record-or-bundle>
aerp new ...
aerp bind <record> <decision> --output <new-record>
aerp bundle-git-ape <deployment-dir> ...
aerp verify <record-or-bundle> --artifact-root <root>
aerp export-intoto <bundle> --output <statement>
aerp export-oscal <bundle> --output <assessment-results>
```

## Agent guardrails

Agents MUST NOT:

- convert `observed` into `passed`;
- convert `inconclusive` or `error` into `failed` or `passed`;
- claim producer authentication from self-declared identity fields;
- mutate fingerprinted evidence in place;
- bind evidence only by a mutable decision identifier;
- update a digest simply because verification failed;
- describe OSCAL projection as regulatory acceptance;
- describe an unsigned statement as signed;
- omit negative evidence to improve a summary;
- expose secrets from logs or configuration.

## Example orchestration

```text
1. ADRP resolver selects active records for the repository and Azure target.
2. Git-Ape generates requirements and infrastructure artifacts.
3. Security, policy, cost, availability, and WAF checks run.
4. AERP captures each report and binds it to the selected ADRP fingerprints.
5. Human approval identifies the exact plan or bundle fingerprint.
6. Git-Ape deploys and stores logs, outputs, and tests.
7. AERP produces and verifies a deployment bundle.
8. The bundle is exported and signed using established attestation tooling.
9. Later drift creates new evidence linked to the same deployment and decisions.
10. Material drift triggers ADRP reconsideration rather than silent acceptance.
```

## Autocomplete and passive Copilot

Autocomplete cannot reliably execute the CLI. Repositories using passive
Copilot should project concise instructions such as:

```markdown
When producing deployment or assessment evidence:
- store artifacts under the deployment evidence directory;
- never report an unexecuted check as passed;
- include the active ADRP record fingerprint;
- run AERP verification in CI.
```

CI remains the enforcement boundary.

## CI pattern

```yaml
- name: Verify AERP evidence
  run: |
    aerp validate .azure/deployments/${DEPLOYMENT_ID}/evidence/bundle.json
    aerp verify \
      .azure/deployments/${DEPLOYMENT_ID}/evidence/bundle.json \
      --artifact-root .azure/deployments/${DEPLOYMENT_ID}
```

Signature verification should be a separate step using the organisation's
chosen identity and trust policy.

## ADRP setup contract

Before AERP capture:

1. validate and verify the ADRP record set;
2. resolve active records for the exact scope and time;
3. preserve the canonical selected record files;
4. provide those files to AERP using repeated `--decision` arguments;
5. ensure the execution system retains the same fingerprints in plans,
   approvals, and traces.

After AERP capture:

1. validate the record or bundle;
2. verify referenced artifact bytes;
3. distinguish local integrity from signature and producer authentication;
4. compare outcomes with ADRP expected evidence and drift triggers;
5. route material differences to ADRP review rather than editing either
   immutable artifact.

See [AERP and ADRP in ISEE](ISEE_INTEGRATION.md) for the complete setup.
