# Architecture Decision Records (ADRs) — RepoPilot

This document records the architectural and technology decisions made during the design and implementation of RepoPilot.

---

## ADR 001: Local LLM Inference via Ollama vs. Cloud APIs

### Context
Autonomous coding agents typically rely on third-party cloud APIs (such as OpenAI or Anthropic). However, this introduces subscription costs, token fees, latency, and data privacy concerns for proprietary enterprise codebases.

### Decision
Adopt **Ollama** (`http://localhost:11434`) with quantized local models (specifically `gemma4:latest`, 8B parameters Q4_K_M) as the primary inferencing engine. Provide a `BaseLLMProvider` interface to support `MockLLMProvider` for deterministic unit testing.

### Consequences
- **Pros:** Zero cloud billing, total data privacy, offline functionality, repeatable benchmark execution.
- **Cons:** Inference speed depends on host hardware; requires 8GB+ RAM. Mitigated by low temperature (`0.1`) and concise JSON schema prompts.

---

## ADR 002: Evidence-Grounded Diagnosis Schema

### Context
Standard LLM completions often assert bug causes without citing verifiable evidence, leading to hallucinations and inaccurate patches.

### Decision
Require that the LLM return structured JSON with an explicit `evidence` array containing:
- `file_path`
- `start_line` and `end_line`
- `snippet`
- `explanation`

### Consequences
- **Pros:** Every diagnosis is grounded in line-specific code facts. The UI can render clickable citations that jump directly to the relevant lines in the source viewer.
- **Cons:** Requires schema post-validation and fallback parsing if the model outputs malformed JSON.

---

## ADR 003: Explicit Patch Review & Conflict Detection

### Context
Agents that write directly to source files risk corrupting developer work or clobbering external edits made while the model was thinking.

### Decision
All patches are formulated as unified diffs and placed in a `pending_review` state. The agent must verify that the target file has not changed on disk (`original_content == current_content`) before applying an approved patch.

### Consequences
- **Pros:** Prevents accidental code loss; gives developer full control over every diff.
- **Cons:** Requires a two-step API interaction (`/patches/generate` followed by `/patches/{id}/approve`).

---

## ADR 004: Strict 2-Iteration Ceiling on Self-Repair Loops

### Context
Autonomous agents given test feedback can loop indefinitely if their hypotheses are flawed, wasting resources and polluting files.

### Decision
Enforce a hard maximum limit of **2 repair iterations** per repair session. If iteration 2 fails, the loop terminates immediately with status `max_iterations_reached` and generates a full audit report.

### Consequences
- **Pros:** Deterministic termination guaranteed; prevents runaway processes.
- **Cons:** Highly complex multi-file bugs may require developer intervention if not solved in 2 attempts (which is an intentional safety feature).
