# code-review — 5-Axis Code Review Skill

## Overview
Review code across 5 axes: design, readability, performance, security, testability.
Output severity-classified findings with concrete fix examples.

## Trigger Conditions
- User says "code review", "review this", "check my code"
- User explicitly calls `/code-review`
- User references a file/directory they want reviewed

## Context Gathering
1. Read every source file in the target scope using `Read` — never guess from file names
2. Run `Grep` for known anti-patterns relevant to the language (e.g. `eval(`, `os.system(`, hardcoded key assignments)
3. Check for function length and nesting depth using shell tools or `Grep`
4. Exclude test files, mock directories, and generated code from findings

## Steps

1. **Determine scope** — resolve the target (file, directory, or git diff). Default to current directory.
2. **Read all source files** — enumerate and read every `.py`, `.ts`, `.js`, `.go`, `.rs`, etc. in scope.
3. **Axis 1 — Design**: Check for:
   - Single Responsibility violations (classes/functions doing too much)
   - Hardcoded dependencies instead of injection
   - Tight coupling between modules (circular imports, direct instantiation)
   - Violations of Open/Closed (switch statements instead of polymorphism where applicable)
4. **Axis 2 — Readability**: Check for:
   - Single-letter or meaningless variables (`a`, `b`, `tmp`, `x1`)
   - Functions over 50 lines
   - Nesting deeper than 4 levels
   - Magic numbers/strings without named constants
   - Inconsistent naming vs project conventions
5. **Axis 3 — Performance**: Check for:
   - N+1 query patterns (DB calls inside loops)
   - Redundant computation inside loops
   - Unnecessary full-table scans or unbounded payloads
   - Blocking I/O in async context
   - Unbounded concurrency (no semaphores, no batch limits)
6. **Axis 4 — Security**: Check for:
   - Missing input validation on external data (URLs, user input, file paths)
   - SQL/path injection via string concatenation or f-strings
   - Hardcoded credentials, API keys, or tokens
   - Overly permissive CORS, CORS wildcards
   - SSRF vectors (unsanitized URLs passed to HTTP clients)
7. **Axis 5 — Testability**: Check for:
   - Global state or singleton dependencies
   - Hard-to-mock external calls (network, filesystem, DB)
   - No clear dependency injection points
   - Side effects in constructors or module-level code

## Output Format

## Code Review Report
Date: <datetime>
Scope: <target>

### Overall Score: <A/B/C/D/F>
| Axis | Grade | Issues |
|------|-------|--------|
| Design | B | 2 |
| Readability | C | 4 |
| Performance | A | 0 |
| Security | D | 1 |
| Testability | B | 1 |

---

### [SEVERITY] Axis N - <Name>: <Brief Title>
**File**: path/to/file.py:42
**Code**: `relevant_code_snippet`
**Risk**: Why this matters in context.
**Fix**:
```python
def concrete_fix_example():
    ...
```

## Important Notes
- Always read actual files with `Read`/`Grep` before reporting — reporting from file names alone wastes reviews
- Severity levels: **CRITICAL** (fix before merge) > **HIGH** (this week) > **MEDIUM** (next sprint) > **LOW** (when convenient)
- Skip findings that only apply to generated code, tests, or mocks
- When proposing a fix, reference the actual file and line number — don't describe it abstractly
- Include at most one finding per unique issue — don't repeat the same pattern across multiple files