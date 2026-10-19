# Learning & Interview Guide — RepoPilot

## 1. Executive Summary & Value Proposition
RepoPilot is an Autonomous AI Software Engineering Agent engineered from first principles to address real-world code repair without relying on expensive cloud LLM APIs or brittle prompt wrappers.

When discussing RepoPilot in technical interviews or presentations, emphasize:
- **Local-First AI:** Built on local Ollama inference (`gemma4:latest`), proving zero-cost, private, offline-capable code reasoning.
- **Defensive Engineering:** Strict security boundaries around path traversal, command allowlisting, diff conflicts, and bounded loops.
- **Evidence-Grounded Intelligence:** Models must cite verified line numbers and file excerpts before proposing root causes.
- **Safety First:** Code modifications are never committed without explicit developer approval.

---

## 2. Key Architecture & Design Patterns

### 2.1 Provider Abstraction Pattern (`BaseLLMProvider`)
- **Problem:** Tying application logic directly to an external API (like OpenAI or Anthropic) creates hard vendor lock-in and fails in disconnected or privacy-critical enterprise environments.
- **Solution:** Implemented `BaseLLMProvider` interface in `backend/app/llm.py` with `generate()`, `is_available()`, and `list_models()`.
- **Impact:** Allowed automated pytest suites to run in seconds using `MockLLMProvider`, while live production runs seamlessly use `OllamaProvider` without touching core logic.

### 2.2 Grounded Evidence Pipeline
- **Problem:** LLMs hallucinate bug causes and fabricate line numbers when asked to diagnose open-ended codebases.
- **Solution:** RepoPilot's `InvestigationEngine` parses Python tracebacks, reads actual code via `read_file_safe()`, formats line-numbered blocks (`0014 | return total / count`), and enforces a Pydantic schema requiring line-range evidence for every diagnostic claim.
- **Impact:** Guarantees that every model citation maps to an actual file and line that can be verified and clicked in the UI.

### 2.3 Explicit Human Approval & Conflict Detection
- **Problem:** Autonomous agents that blindly overwrite files can destroy developer work or introduce merge conflicts if files are changed externally.
- **Solution:** `PatchEngine` produces unified diffs (`a/...` vs `b/...`) and stores original file snapshots. Prior to applying, RepoPilot validates that the live disk content matches the exact snapshot the patch was derived from.
- **Impact:** Outdated patches or dirty workspaces are caught with clear conflict warnings.

### 2.4 Bounded Self-Repair Loop
- **Problem:** Autonomous retry loops can enter infinite recursion or runaway generation loops if tests repeatedly fail.
- **Solution:** `RepairLoopOrchestrator` implements a strict 2-attempt finite state machine. Iteration 1 failure feedback is injected into Iteration 2. If Iteration 2 fails, the loop terminates deterministically with an audit trail.

---

## 3. High-Frequency Interview Questions & Answers

### Q1: "Why local LLMs like Ollama instead of GPT-4 or Claude 3.5?"
> **Answer:** Enterprise software repositories often contain proprietary intellectual property and regulated data that cannot be sent to cloud endpoints. RepoPilot demonstrates that modern 8B-parameter open models (such as `gemma4:latest`) quantized to 4-bits provide high precision for code repairs when given structured prompts, AST contexts, and regression test feedback—with zero API billing and complete privacy.

### Q2: "How do you protect against arbitrary code execution when running tests?"
> **Answer:** RepoPilot implements multiple layers of defensive isolation:
> 1. **Command Allowlisting:** Rejects arbitrary shell execution. Only `python -m pytest` is permitted.
> 2. **Path Sanitization:** Test targets cannot contain `..`, leading slashes, or shell operators (`;`, `&&`, `|`).
> 3. **Subprocess Isolation:** Commands run in isolated working directories with repo-scoped `PYTHONPATH` environments.
> 4. **Execution Timeouts:** Strict 30-second timeouts kill runaway processes or infinite loops.
> 5. **Output Caps:** Stdout/stderr streams are truncated at 64KB to prevent memory exhaustion.

### Q3: "How does the agent know if its fix worked?"
> **Answer:** RepoPilot does not trust model self-reports. It applies the patch and executes the actual test suite using `TestRunner`. The status is only marked `VERIFIED` when pytest returns exit code 0 with 0 failures and 0 errors. If tests fail, the exact failure traceback is fed back into the bounded repair loop.
