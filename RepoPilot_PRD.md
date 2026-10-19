# RepoPilot — Product Requirements Document (PRD)

**Project type:** AI-powered software engineering agent  
**Target users:** Individual developers, students, and small engineering teams  
**Primary objective:** Investigate repository-level bugs, propose reviewable code changes, and verify those changes through controlled test execution  
**Implementation constraint:** Free, local-first, and provider-agnostic  
**Initial scope:** Python repositories; architecture should allow other languages later  
**Status:** Proposed specification — implementation and evaluation results must be documented honestly

---

## 1. Executive Summary

RepoPilot is a local-first AI software engineering agent that helps developers understand unfamiliar codebases, investigate bugs, propose minimal patches, and validate changes with tests.

Unlike a basic coding chatbot, RepoPilot operates on a real repository and follows a visible, auditable workflow:

1. Inspect and index the repository.
2. Translate the user's request into a bounded task.
3. Locate relevant files and symbols.
4. Gather evidence for a diagnosis.
5. Propose a patch and explain its rationale.
6. Ask for approval before modifying files.
7. Run approved tests in a restricted environment.
8. Inspect failures and optionally revise the patch within configured limits.
9. Report exactly what was changed and what was verified.

RepoPilot does not guarantee that generated code is correct. It must distinguish between a proposed fix, a patch that applies, a test that passes, and a fix whose behavior has been independently validated.

## 2. Problem Statement

Developers frequently spend time understanding unfamiliar repositories, locating the source of bugs, tracing dependencies, writing regression tests, and checking whether proposed changes introduce regressions.

A general-purpose LLM can suggest plausible code, but may:
- Miss relevant code elsewhere in the repository.
- Invent APIs, functions, or file paths.
- Make unnecessarily broad changes.
- Claim tests passed without executing them.
- Misinterpret a failing test or repeatedly apply ineffective fixes.
- Run unsafe commands if granted unrestricted tool access.

RepoPilot aims to reduce this friction while preserving developer control and making the agent's work inspectable.

## 3. Goals

### 3.1 Primary goals

- Understand a selected local Git repository.
- Find relevant files using lexical and semantic search.
- Support evidence-based bug investigation.
- Generate minimal, reviewable patches.
- Show diffs and request approval before writing changes.
- Execute allowlisted tests in an isolated workspace.
- Capture command output, exit codes, and test results.
- Limit retries, execution time, changed files, and resource use.
- Maintain an audit trail for each task.
- Evaluate the system against a repeatable benchmark.

### 3.2 Non-goals for the MVP

- Fully autonomous production deployments.
- Automatically pushing commits or opening pull requests.
- Unrestricted terminal or internet access.
- Guaranteeing bug-free code or eliminating hallucinations.
- Supporting every programming language equally well.
- Training a foundation model from scratch.
- Replacing code review or developer judgment.
- Processing private repositories through external APIs by default.

## 4. Target Users and Use Cases

### Primary user

A developer or computer science student working with a local repository who wants help investigating bugs and validating fixes.

### Core use cases

1. **Explain a repository:** Describe its structure, entry points, main modules, and test commands.
2. **Investigate a bug:** Trace a reported failure to relevant code and present supporting evidence.
3. **Propose a fix:** Generate a minimal patch and explain why it addresses the suspected cause.
4. **Create a regression test:** Add a test that reproduces the bug before the fix, where feasible.
5. **Validate a patch:** Run approved tests and report exact outcomes.
6. **Recover from test failures:** Inspect failure output and suggest a bounded revision.
7. **Review changes:** Summarize the diff, potential risks, and tests that were not run.

## 5. Product Principles

- **Evidence before edits:** The agent should inspect relevant code before proposing changes.
- **Human approval:** No file modification without explicit approval in the MVP.
- **Least privilege:** Tools receive only the access required for the current step.
- **Reproducibility:** Record prompts, model/provider, configuration, tool calls, diffs, and test results.
- **Honest verification:** Never represent an unexecuted test as passing.
- **Small changes:** Prefer focused patches over broad rewrites.
- **Provider independence:** Separate model interfaces from orchestration and application logic.
- **Local-first privacy:** Keep repository content on the user's machine unless the user explicitly configures a remote provider.

## 6. Functional Requirements

### FR-01: Repository Selection

- The user selects a local repository directory.
- The system validates the path and detects the repository root.
- The system identifies the language, common project manifests, Git status, and available test configuration.
- The system warns about uncommitted changes.
- The system must not overwrite or discard existing user changes.

**Acceptance criteria**
- Invalid paths produce a clear error.
- Existing uncommitted changes are preserved.
- The repository root and detected project type are visible to the user.

### FR-02: Repository Exploration and Indexing

- Build a file tree and searchable inventory of supported source files.
- Exclude `.git`, virtual environments, dependency directories, build outputs, caches, and configured ignored files.
- Respect `.gitignore` where practical.
- Support lexical search as a dependable baseline.
- Optionally add embeddings and semantic retrieval.
- Show the source file and line range for retrieved evidence.
- Enforce file-size and repository-size limits.

**Acceptance criteria**
- Search results refer to real files and valid line ranges.
- Binary files and configured secrets are not indexed as ordinary source.
- The UI explains when a file was excluded or could not be parsed.

### FR-03: Task Planning

- Convert the user's request into a bounded task.
- Produce a plan with steps, expected evidence, and validation criteria.
- Ask clarifying questions when the request is ambiguous or too broad.
- Enforce maximum steps, tool calls, runtime, and revision attempts.

**Acceptance criteria**
- The user can inspect the plan before execution.
- The plan cannot authorize a prohibited operation.
- The system stops and explains why when configured limits are reached.

### FR-04: Bug Investigation

- Search for relevant functions, routes, symbols, tests, and error messages.
- Inspect source files and nearby dependencies.
- Maintain an evidence list containing file paths and line ranges.
- Present a diagnosis with supporting and contradictory evidence.
- Clearly label hypotheses that have not been verified.

**Acceptance criteria**
- Each code-based claim links to a real file and line range when available.
- The agent can report insufficient evidence instead of fabricating a diagnosis.

### FR-05: Patch Generation

- Generate a unified diff or equivalent structured patch.
- Explain the purpose and risk of each material change.
- Prefer minimal changes.
- Validate that target files exist and that the patch applies cleanly.
- Detect conflicts with changes made since investigation began.

**Acceptance criteria**
- The diff is displayed before approval.
- No source file is modified before explicit approval.
- Invalid or conflicting patches are rejected without destroying user changes.

### FR-06: Human Approval

The user must separately approve:
- Applying a proposed patch.
- Running commands not already on the configured allowlist.
- Any action that increases permissions or changes the execution boundary.

The user can reject the patch, request revisions, or cancel the task.

### FR-07: Controlled Test Execution

- Support explicitly configured commands, such as selected `pytest` invocations.
- Run tests in a disposable worktree, container, or equivalent isolated environment where available.
- Use timeouts, output limits, and resource limits.
- Capture the exact command, exit code, standard output, standard error, and duration.
- Never silently install dependencies or execute arbitrary setup scripts.
- Do not expose host secrets or credentials to the execution environment.

**Acceptance criteria**
- Test status reflects the actual process exit code and parsed test results.
- Timeouts and execution errors are distinct from test failures.
- The original working tree remains recoverable and is not overwritten.
- If adequate isolation is unavailable, the UI clearly warns the user and requires an explicitly configured safer alternative.

### FR-08: Bounded Repair Loop

- After a test failure, the agent may inspect the output and propose another patch.
- Every new patch must be shown for approval.
- The number of repair attempts is configurable and limited.
- The agent must stop when the evidence is insufficient or attempts are exhausted.

**Acceptance criteria**
- Every attempt has its own diff and test record.
- The agent cannot loop indefinitely.
- The final summary distinguishes passing tests from unresolved failures.

### FR-09: Task History and Audit Trail

Record:
- Task request and task identifier.
- Repository identifier and revision/commit where available.
- Model/provider and relevant configuration.
- Plan and evidence references.
- Tool invocations and outcomes.
- Proposed and approved diffs.
- Test commands, outputs, exit codes, and duration.
- Final status and known limitations.

Avoid storing secrets or unnecessarily copying source files into logs.

### FR-10: User Interface

Provide:
- Repository selector.
- Repository tree and search.
- Task input.
- Visible agent plan and progress.
- Evidence panel with source links.
- Diff review panel.
- Test output panel.
- Approval and cancellation controls.
- Task history and final report.

The interface must remain usable when a model is unavailable or a tool fails.

## 7. Non-Functional Requirements

### Security

- Treat repository content, issue descriptions, comments, README files, and test output as untrusted data.
- Defend against prompt injection in repository files.
- Never let text found in a repository override system safety policies.
- Use an allowlist for executable tools and commands.
- Apply path traversal checks and prevent writes outside the selected workspace.
- Keep secrets out of prompts, logs, and test containers.
- Require explicit permission for network access.
- Prefer a disposable container or worktree with restricted permissions.
- Make destructive operations unavailable by default.

### Reliability

- Tool calls must return structured success/failure results.
- Network/model errors must not be confused with code errors.
- Retries must be bounded.
- Persist enough task state to recover from an interrupted session where practical.
- All final status claims must be derived from recorded execution results.

### Performance

Initial targets for a modest local machine; revise after measuring:
- Repository inventory for a small project: under 10 seconds, excluding model startup.
- Lexical search: under 2 seconds for a small-to-medium repository.
- UI should display progress during long model calls and test runs.
- Model generation time is reported separately from orchestration time.

These are targets, not established results.

### Privacy

- Local inference is the default.
- No source code is sent to a remote provider unless the user explicitly configures and consents to it.
- Clearly indicate when a remote model is selected.
- Allow task history to be cleared.
- Exclude environment files, credentials, and configured sensitive paths.

### Accessibility and Usability

- Clear statuses: planning, investigating, awaiting approval, testing, completed, failed, cancelled.
- Show errors in actionable language.
- Make diffs and test output copyable.
- Avoid relying on color alone to communicate state.

## 8. Proposed Technical Architecture

### Frontend
- React
- TypeScript
- Vite
- A lightweight component library or custom CSS
- Server-Sent Events (SSE) or WebSockets for task progress

### Backend
- Python
- FastAPI
- Pydantic for validated request/response schemas
- Background task runner for long-running agent jobs

### Agent orchestration
- A small explicit state machine initially; optionally LangGraph if its checkpointing and graph abstractions prove useful.
- Provider interface for chat and structured output.
- Tool registry with typed schemas and permission policies.
- Bounded orchestration loop with explicit stop conditions.

### Repository intelligence
- Python standard library and `pathlib` for safe file inventory.
- `ripgrep` or a Python lexical-search implementation.
- Python AST parsing where useful.
- Optional sentence-transformer embeddings for semantic search.
- Optional reranker only if evaluation demonstrates an improvement.

### Execution and testing
- Git worktrees for isolated patch experiments.
- Docker or another configured sandbox for test execution.
- pytest for the initial supported ecosystem.
- No automatic arbitrary command execution.

### Persistence
- SQLite for the MVP.
- Store task metadata, event records, patch metadata, and test results.
- Avoid storing duplicate full source files.

### Local model runtime
- Ollama or another compatible local inference server.
- Select a model that fits available RAM and performance requirements.
- Keep model choice configurable.
- Support deterministic/mock model adapters for unit tests.

## 9. High-Level Workflow

1. User selects a repository.
2. RepoPilot checks its path, Git status, size, and project type.
3. User describes a bug or task.
4. Planner creates a bounded plan.
5. Repository tools retrieve source and test evidence.
6. Agent presents a diagnosis and confidence rationale.
7. Agent proposes a patch.
8. User reviews and approves or rejects the patch.
9. Approved patch is applied in an isolated worktree.
10. Configured tests execute under limits.
11. Agent inspects test results and may propose a bounded revision.
12. User approves any subsequent patch.
13. RepoPilot produces an audit report and final status.

## 10. API Sketch

These endpoints are illustrative and may be adjusted during implementation.

- `POST /api/repositories` — register a local repository.
- `GET /api/repositories/{id}` — retrieve repository metadata.
- `POST /api/repositories/{id}/index` — index supported files.
- `POST /api/tasks` — create a task.
- `GET /api/tasks/{id}` — get current task state.
- `GET /api/tasks/{id}/events` — stream task events.
- `GET /api/tasks/{id}/evidence` — retrieve evidence references.
- `GET /api/tasks/{id}/diff` — retrieve the proposed diff.
- `POST /api/tasks/{id}/approve-patch` — approve a specific diff version.
- `POST /api/tasks/{id}/reject-patch` — reject a proposed diff.
- `POST /api/tasks/{id}/run-tests` — request approved test execution.
- `POST /api/tasks/{id}/cancel` — cancel a running task.
- `GET /api/tasks/{id}/report` — retrieve the final report.

Every endpoint must enforce repository ownership, task state, and permission checks.

## 11. Data Model Sketch

### Repository
- `id`
- `display_name`
- `canonical_path`
- `detected_language`
- `git_revision`
- `created_at`

### Task
- `id`
- `repository_id`
- `request`
- `status`
- `plan_json`
- `model_provider`
- `model_name`
- `created_at`
- `completed_at`

### TaskEvent
- `id`
- `task_id`
- `event_type`
- `timestamp`
- `safe_payload_json`

### Patch
- `id`
- `task_id`
- `version`
- `diff`
- `status`
- `approved_at`

### TestRun
- `id`
- `task_id`
- `patch_version`
- `command`
- `exit_code`
- `status`
- `duration_ms`
- `output_reference`

Do not persist raw secrets, authentication tokens, or unnecessary repository contents.

## 12. Evaluation Plan

A credible portfolio requires measured outcomes, not only a demo.

### Dataset

Build a small, versioned benchmark from:
- Public, permissively licensed repositories with known issues.
- Small synthetic repositories with deliberately seeded bugs.
- Regression tests and known expected behavior.
- Unanswerable or ambiguous debugging tasks.

For every task, record the repository revision, bug description, expected behavior, reproduction steps, relevant files where known, and test outcome. Check repository licenses before redistributing code.

### Baselines

Compare RepoPilot against:
1. A simple lexical-search-plus-LLM baseline.
2. RepoPilot with repository-aware retrieval.
3. RepoPilot with retrieval plus test-feedback repair.

Use the same benchmark and resource limits for each configuration.

### Metrics

- **Task success rate:** fraction of tasks where the intended behavior is verified.
- **Patch application rate:** fraction of generated patches that apply cleanly.
- **Test pass rate:** fraction of tasks whose required tests pass after the patch.
- **Regression rate:** fraction of fixes that cause previously passing tests to fail.
- **Evidence precision:** proportion of surfaced evidence references judged relevant.
- **Localization accuracy:** whether the relevant fault location appears among the top-k files or symbols.
- **Human approval rate:** fraction of proposed patches approved by reviewers; interpret alongside review quality.
- **Tool-call success rate:** fraction of tool calls that complete as expected.
- **Latency:** median and 95th-percentile task duration.
- **Resource use:** peak memory and CPU time where measurable.

Report sample size, model configuration, failures, and uncertainty. Do not claim an improvement until the benchmark has actually been run.

### Initial acceptance targets

These are provisional goals, not promised performance:
- All test execution is associated with a recorded command and exit code.
- No patch is applied without approval.
- All benchmark tasks have reproducible inputs and recorded outcomes.
- At least 80% patch application on the initial benchmark.
- At least 60% verified task success on a deliberately small, scoped benchmark.
- No known destructive action can run through the default tool configuration.

A low score is still useful if reported honestly and used to guide iteration.

## 13. MVP Scope and Milestones

### Phase 1 — Repository explorer
- Register a local Python repository.
- Show a file tree and Git status.
- Implement safe lexical search.
- Add basic project/test detection.

**Exit criterion:** users can locate real files and inspect source excerpts.

### Phase 2 — Evidence-backed investigation
- Add task creation and visible plans.
- Retrieve relevant files and line ranges.
- Produce structured diagnoses with evidence references.
- Add task event history.

**Exit criterion:** every code reference resolves to a real source location.

### Phase 3 — Patch review
- Generate unified diffs.
- Validate patch applicability.
- Show side-by-side or unified diffs.
- Add approve/reject controls.

**Exit criterion:** rejected patches never alter source files; approved patches are applied only to the intended workspace.

### Phase 4 — Test execution
- Create a disposable worktree.
- Configure allowlisted test commands.
- Enforce timeouts and output limits.
- Capture exact execution results.

**Exit criterion:** the UI accurately distinguishes pass, fail, timeout, and execution error.

### Phase 5 — Bounded repair loop
- Inspect failures.
- Permit a small configurable number of revision attempts.
- Require approval for every new patch.
- Produce a final verification report.

**Exit criterion:** loops terminate within configured limits and all attempts are recorded.

### Phase 6 — Evaluation and portfolio release
- Create the benchmark.
- Run baselines and ablations.
- Document results and limitations.
- Add Docker instructions, architecture diagrams, sample tasks, tests, and a clear README.

**Exit criterion:** another developer can reproduce the core demo and evaluation locally.

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Incorrect code changes | Human approval, regression tests, minimal patches |
| Prompt injection from repository files | Treat all repository content as untrusted data; keep policies outside model-controlled context |
| Unsafe test commands | Explicit allowlists, sandboxing, timeouts, resource limits |
| Local model is too slow or weak | Small scoped tasks, configurable models, deterministic tests, optional provider interface |
| Poor retrieval | Evaluate lexical search first, add semantic retrieval only when it helps |
| False confidence | Separate hypotheses from verified facts; display evidence and test outcomes |
| Scope grows too large | Start with Python bug-fixing workflows only |
| Benchmark overfitting | Use held-out tasks and report limitations |
| Secrets leak into logs or prompts | Exclude sensitive files and redact configured patterns |

## 15. Definition of Done

The MVP is complete when a user can:

1. Select a supported local Python repository.
2. Describe a bounded bug-fixing task.
3. See a plan and inspect the evidence gathered.
4. Review a proposed patch.
5. Approve or reject the patch.
6. Run approved tests in the configured isolated environment.
7. Inspect actual test results and relevant logs.
8. Receive an accurate final report showing changes, verification status, and unresolved issues.
9. Reproduce a documented evaluation run.

## 16. Portfolio Deliverables

- Public Git repository with a clear license.
- Architecture diagram and component descriptions.
- Local setup guide and model configuration instructions.
- Example repository and reproducible demonstration.
- Automated unit and integration tests.
- Benchmark dataset or reproducible dataset-generation instructions.
- Evaluation report comparing baselines.
- Security model and known limitations.
- Short demo video or GIF.
- Interview notes explaining design decisions, trade-offs, failures, and improvements.

## 17. Future Enhancements

Only after the MVP and evaluation are reliable:
- Add JavaScript/TypeScript repository support.
- Add issue tracker integration.
- Add optional pull-request generation behind explicit approval.
- Add static analysis and lint feedback.
- Add dependency vulnerability analysis using local or explicitly configured tools.
- Add team workspaces and role-based access.
- Add optional remote model providers with clear privacy controls.

## 18. Final Product Positioning

**RepoPilot is a local-first AI software engineering agent that investigates repository-level bugs, proposes human-reviewable patches, and validates changes through controlled test execution.**

Its portfolio strength comes from measurable reliability, tool safety, source-grounded diagnosis, and transparent verification—not from claiming that an LLM can write code autonomously.
