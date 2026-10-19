# Security Architecture & Sandbox Controls — RepoPilot

RepoPilot is engineered for safe execution over local codebases. This document specifies the threat model, mitigation strategies, and sandbox enforcement rules.

---

## 1. Threat Model & Mitigations

| Threat | Risk Level | Mitigation Mechanism |
| :--- | :--- | :--- |
| **Directory Traversal** (`../../etc/passwd`) | Critical | `resolve_safe_path()` resolves target paths against repository root and raises `SecurityException` if outside bounds. |
| **Arbitrary Command Execution** | Critical | Command execution is strictly allowlisted to `python -m pytest`. Arbitrary bash/powershell strings are rejected. |
| **Denial of Service / Infinite Loops** | High | Every test subprocess has an enforced timeout (default 30s) and is forcefully killed (`process.kill()`) if exceeded. |
| **Memory Exhaustion via Log Flooding** | Medium | Captured `stdout` and `stderr` streams are truncated at 64KB max (`MAX_OUTPUT_BYTES`). |
| **Silent File Overwrite / Drift Conflict** | High | `PatchEngine` validates that the live disk content matches the exact snapshot the patch was derived from before applying. |
| **Runaway Agent Loops / Resource Drain** | High | `RepairLoopOrchestrator` enforces a hard ceiling of 2 iterations. Sessions terminate immediately when reached. |
| **Data Leakage / Telemetry** | High | All inferencing is executed locally via Ollama (`http://localhost:11434`). Zero code or telemetry is transmitted to external clouds. |

---

## 2. Command Execution Security Policy

RepoPilot adheres to a zero-trust model regarding LLM-generated shell commands:
1. **No LLM Shell Access:** The LLM is never given a bash tool or terminal prompt.
2. **Deterministic Commands Only:** Commands are constructed programmatically:
   ```python
   cmd = ["python", "-m", "pytest", sanitized_target]
   ```
3. **Environment Isolation:** Subprocesses run with an isolated environment where `PYTHONPATH` points specifically to the repository root and `PYTHONDONTWRITEBYTECODE=1` prevents bytecode littering.

---

## 3. Human-in-the-Loop Approval Model

- **Phase 1-2 (Explorer & Investigator):** Read-only operations. No file modifications permitted.
- **Phase 3 (Patch Review):** Synthesized patches are placed in `pending_review` status. The developer must inspect the unified diff and click **"Approve & Apply"** before disk writes occur.
- **Phase 5 (Repair Loop):** Executes bounded verification within the user-approved scope and logs every action into an immutable audit trail.
