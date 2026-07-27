# Secret compromise

## Immediate
1. Rotate compromised credentials in the secret manager.
2. Refresh ExternalSecret / Kubernetes Secret.
3. Restart API + workers to pick up new values.
4. Revoke old LLM/API keys and DB passwords.

## Follow-up
1. Audit access logs and audit trail for abuse.
2. Update `.env` locally; never commit secrets.
3. Review who had access to the leaked secret.
