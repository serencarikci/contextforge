# Security Policy

## Supported versions

This project is in early development. Security fixes are applied on the default branch.

## Reporting a vulnerability

Please do **not** open a public issue for security vulnerabilities.

Report vulnerabilities privately to the maintainers and include:

* A description of the issue
* Steps to reproduce
* Potential impact
* Any suggested remediation

We will acknowledge receipt and work on a fix as quickly as practical.

## Security baseline (current release)

* No production credentials are hardcoded.
* Containers run as a non-root user.
* API errors do not expose internal stack traces.
* Request bodies and secrets are not logged.
* Configuration is environment-based.
* Dependencies are locked via `uv.lock`.
* External dependency checks use timeouts.
* CORS is disabled by default.
* OpenAPI docs are disabled in production by default.

Authentication and authorization will be introduced in later commits.
