# Deploy failure

## Symptoms
- Helm/CD job fails, pods CrashLoopBackOff, or migrate Job fails.

## Checks
1. `kubectl get pods,jobs -n contextforge`
2. Inspect migrate Job logs first.
3. Confirm secrets exist (`contextforge-app`) and ConfigMap values match the environment.
4. Verify image tag exists in GHCR.

## Mitigation
1. Fix migration or secret issue.
2. Re-run CD / `helm upgrade`.
3. If image is bad, roll back to previous tag (see rollback runbook).
