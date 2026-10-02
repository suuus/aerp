# Security policy

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not
include credentials, private evidence, or sensitive deployment artifacts in a
public issue.

## Security model

AERP fingerprints detect local content modification. They are not digital
signatures and do not authenticate producers.

For high-consequence use:

- sign exported statements with an established system;
- verify producer identity against an explicit trust policy;
- protect evidence storage and artifact roots;
- redact secrets before capture;
- separate public metadata from restricted artifacts;
- establish retention, revocation, and access-control rules.

Treat evidence and deployment logs as potentially sensitive.
