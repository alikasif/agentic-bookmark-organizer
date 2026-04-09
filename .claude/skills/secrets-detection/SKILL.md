# secrets-detection — Scanned for Leaked Credentials in Code

## Overview
Scan source code and configuration files for accidentally committed secrets, API keys, passwords, and tokens. Report findings with severity ratings and mitigation steps.

## Trigger Conditions
- User says "check for secrets", "scan for credentials", "secrets review", "check for leaked keys"
- User explicitly calls `/secrets-detection`
- User suspects credentials were committed and wants verification

## Context Gathering
1. Read all source, config, and environment files using `Read`
2. Run `Grep` with case-insensitive searches for common secret patterns
3. Check `.gitignore` to see what should already be excluded
4. Scan commit history with `git log` for any recently added secrets

## Steps

1. **Determine scope** — resolve target path, default to repository root
2. **Search for hardcoded secrets** using these patterns:
   - API keys: `(api_key|apikey|api-key)\s*=\s*["']?[a-zA-Z0-9]`
   - Passwords: `(password|passwd|pwd)\s*=\s*["']?[^\s]`
   - Secret keys: `(secret_key|secret|client_secret)\s*=\s*["']?[^\s]`
   - Tokens: `(token|auth_token|access_token|bearer)\s*=\s*["']?[^\s]`
   - AWS keys: `(AKIA[0-9A-Z]{16}|aws_secret_access_key)`
   - Private keys: `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`
   - Database URLs: `(postgres|mysql|mongodb|redis)://\S+:\S+@`
   - JWT secrets: `(jwt_secret|jwt_key)\s*=\s*`
3. **Filter false positives**:
   - Ignore test fixtures, mock data, and dummy values
   - Skip environment variables (e.g. `os.environ["API_KEY"]`)
   - Allow placeholder patterns (`"sk-xxx"`, `"your-api-key-here"`, `***`, `xxx`)
   - Check if files are already in `.gitignore`
4. **Classify findings** by severity:
   - **CRITICAL**: Real secrets in production code (not tests/mocks)
   - **HIGH**: Real secrets in non-obvious locations or committed to public repos
   - **MEDIUM**: Secrets in test files that could be exposed
   - **LOW**: Near-secrets that need investigation but are likely safe
5. **Provide remediation** for each finding

## Output Format

## Secrets Detection Report
Date: <datetime>
Scope: <target>

### Summary
| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |
| LOW | 2 |

### Findings

#### [CRITICAL] Hardcoded API Key
**File**: `src/config.py:15`
**Pattern matched**: `api_key = "sk-ant-api03-xxxx"`
**Risk**: Exposed in git history, immediately exploitable.
**Remediation**:
```python
# Before
api_key = "sk-ant-api03-xxxx"

# After
api_key = os.environ["API_KEY"]
```
**Action**: Rotate the exposed key immediately after removing it from code.

---

### Cleanup Checklist
- [ ] Remove secrets from all affected files
- [ ] Rotate all exposed credentials
- [ ] Add affected patterns to `.gitignore` or pre-commit hooks
- [ ] Consider installing `gitleaks` or `detect-secrets` as prevention

## Important Notes
- Never echo full secret values in your report — use redacted form: `sk-ant-xxxx`
- If a secret has been committed, advise the user to rotate it even after removal (it's in git history)
- Include `detect-secrets` or `gitleaks` pre-commit hook setup as prevention
- False positives should be documented but marked clearly as such
