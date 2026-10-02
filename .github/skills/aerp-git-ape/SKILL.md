---
name: aerp-git-ape
description: Convert a Git-Ape .azure/deployments execution trace into a portable AERP evidence bundle.
---

# Bundle Git-Ape evidence

1. Locate one deployment directory under `.azure/deployments/`.
2. Identify the execution identity, target Azure scope, Git-Ape version, and
   applicable ADRP decision records.
3. Run:

   ```bash
   aerp bundle-git-ape .azure/deployments/<id> \
     --identity "<workflow-or-human-identity>" \
     --producer-version "<git-ape-version>" \
     --target "<subscription/resource-group>" \
     --decision path/to/ADR.json \
     --structure path/to/Structure.json \
     --output .azure/deployments/<id>/evidence/bundle.json
   ```

4. Verify against the deployment directory:

   ```bash
   aerp verify .azure/deployments/<id>/evidence/bundle.json \
     --artifact-root .azure/deployments/<id>
   ```

5. Preserve failed and error artifacts. Their presence is evidence; it is not a
   successful result.

The adapter recognises the documented Git-Ape deployment and drift artifacts.
Unknown files are left untouched and are not silently claimed as evidence.
