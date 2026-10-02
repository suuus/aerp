---
name: aerp-verify
description: Validate AERP structures, fingerprints, decision bindings, and referenced artifact digests.
---

# Verify evidence

1. Run `aerp validate <path>` for structural and fingerprint validation.
2. Run `aerp inspect <path>` for a human-readable machine summary.
3. Run `aerp verify <path> --artifact-root <root>` to re-hash every referenced
   artifact.
4. Treat a missing or changed artifact as verification failure.
5. Use `--allow-missing-artifacts` only for explicit metadata inspection; never
   describe that result as verified evidence.

Verification proves internal consistency and artifact identity. It does not
prove that a producer was trustworthy unless a separate signature and identity
verification process establishes that.
