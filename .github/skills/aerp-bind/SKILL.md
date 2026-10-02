---
name: aerp-bind
description: Bind an AERP record to the immutable fingerprint of an ADRP decision record.
---

# Bind evidence to intent

1. Confirm the evidence record and ADRP decision record are the intended pair.
2. Run:

   ```bash
   aerp bind evidence.json decision.json --output evidence.bound.json
   ```

3. Treat the output as a new immutable evidence artifact. Do not overwrite the
   original.
4. Run `aerp inspect` to show the exact `decision_id`, `record_id`,
   `record_version`, and `record_fingerprint`.

A binding proves which record the evidence refers to. It does not prove that
the decision was authoritative, applicable, or complied with.
