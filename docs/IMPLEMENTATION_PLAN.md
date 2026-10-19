# RepoPilot — Implementation Plan

This document details the multi-phase implementation roadmap for RepoPilot, grounded in the PRD (`docs/PRD.md`) and the Master Engineering Prompt requirements.

---

## Environment & Prerequisites Assessment

- **OS:** Windows 11
- **Python:** Python 3.14.4
- **Node.js:** v25.9.0 / npm 11.12.1
- **Git:** Git 2.51.0
- **Ollama:** 0.40.3
- **Installed Models:** `gemma4:latest` (9.6 GB, local inference ready)
- **Target Architecture:**
  - Backend: FastAPI, Pydantic, SQLite, pytest
  - Frontend: React 18/19, TypeScript, Vite, Vanilla CSS design tokens & CSS modules, Lucide React, Framer Motion
  - LLM Provider: Configurable Ollama provider interface with graceful fallback when offline

---

## Phase Breakdown & Acceptance Criteria

### Phase 0: Inspection, Foundations & Planning (Current Phase)
- [x] Inspect actual workspace, OS, available tools, models, and PRD.
- [x] Place `docs/PRD.md` in repository.
- [x] Create `docs/IMPLEMENTATION_PLAN.md` with clear verification criteria.
- [ ] Establish project layout (`backend/`, `frontend/`, `docs/`, `benchmarks/`).
- [ ] Initialize backend environment and frontend Vite template.

### Phase 1: Repository Explorer (Vertical Slice: Core Inspection & Safe Search)
- **Objective:** Select a local Python repository, inspect structure safely, view files with line numbers, and execute fast lexical search.
- **Backend Tasks:**
  - Safe path resolver ensuring no traversal outside selected repository or allowed paths.
  - File tree scanner respecting `.gitignore`, excluding `.git`, `.venv`, `node_modules`, `__pycache__`, large/binary files.
  - Safe file reader with line-based slicing, line numbering, and byte caps.
  - Lexical code search (token/regex matching with context lines).
  - Repository manifest detection (`pyproject.toml`, `requirements.txt`, `setup.cfg`, `pytest.ini`).
  - FastAPI endpoints:
    - `POST /api/repositories` (register and validate)
    - `GET /api/repositories` (list active/recent)
    - `GET /api/repositories/{id}/tree` (file tree)
    - `GET /api/repositories/{id}/files?path=...&start=...&end=...` (file contents)
    - `GET /api/repositories/{id}/search?q=...` (symbol and text search)
- **Frontend Tasks:**
  - Refined developer-first dark theme design system (`index.css` tokens).
  - Sidebar layout: Repo selector, Explorer tree, Navigation.
  - File tree viewer with expandable directories and icons.
  - Source excerpt viewer with line numbers and syntax styling.
  - Interactive search bar with instant results and line jump.
- **Verification & Acceptance Criteria:**
  - Backend unit tests for path validation, ignore filters, file reading limits, and search.
  - User can select a local Python folder, browse tree, click a file, view lines with correct numbering, and search for symbols.

### Phase 2: Bug Investigation Engine
- **Objective:** Model-assisted investigation gathering evidence from code before forming hypotheses.
- **Backend Tasks:**
  - [x] LLM Provider abstraction (`BaseLLMProvider`, `OllamaProvider`, `MockProvider` for deterministic tests).
  - [x] Health check & model selector (`GET /api/system/status`).
  - [x] Evidence collector: extracts relevant code slices, function definitions, call sites, and test cases.
  - [x] Structured investigation prompt and Pydantic output schema:
    - Root cause hypothesis
    - Supporting evidence (file paths and line ranges)
    - Suggested fix strategy
    - Recommended regression test
    - Known uncertainties
  - [x] Investigation endpoint (`POST /api/investigate`).
- **Frontend Tasks:**
  - [x] Bug report input (issue description, traceback, optional constraints).
  - [x] Real-time investigation status tracker and Ollama engine status indicator.
  - [x] Evidence Panel: Clickable file/line citations opening directly in source viewer.
  - [x] Diagnosis Card: Clear visual distinction between concrete facts and model hypotheses.
- **Verification & Acceptance Criteria:**
  - [x] Automated tests with MockProvider verifying diagnosis structure and evidence verification (`backend/tests/test_investigation.py`).
  - [x] Local Ollama integration connecting to `gemma4:latest`.

### Phase 3: Patch Generation, Validation & Review
- **Objective:** Generate minimal unified diffs, review changes with side-by-side or unified view, and require explicit approval before applying.
- **Backend Tasks:**
  - [x] Patch generation engine instructing model to output standard unified diffs or structured replacements (`backend/app/patcher.py`).
  - [x] Diff validator: verifies target file existence, line anchors, hunk applicability without conflicts.
  - [x] Explicit human approval workflow:
    - [x] `POST /api/patches/generate`
    - [x] `GET /api/patches/{id}`
    - [x] `POST /api/patches/{id}/approve`
    - [x] `POST /api/patches/{id}/reject`
- **Frontend Tasks:**
  - [x] Polished Diff Viewer (`frontend/src/components/DiffViewer.tsx`) with added/removed line counters and syntax styling.
  - [x] Explicit patch approval action bar with version tagging (`v1`) and status pills (`pending_review`, `applied`, `rejected`).
  - [x] Diff reject / revise feedback controls.
- **Verification & Acceptance Criteria:**
  - [x] Automated tests verifying rejecting leaves source untouched and only approved patches apply (`backend/tests/test_patcher.py`).
  - [x] Outdated or modified file conflict detection prevents silent overwrite.

### Phase 4: Controlled Test Runner & Verification
- **Objective:** Run allowlisted tests inside isolated execution boundaries with strict timeouts and output capture.
- **Backend Tasks:**
  - [x] Command allowlist parser (`python -m pytest`). Disallow arbitrary shell execution (`backend/app/runner.py`).
  - [x] Subprocess runner with resource caps, execution timeouts (e.g., 30s), output truncation (64KB max).
  - [x] Test result parser: extracts passed, failed, errors, durations, and tracebacks.
  - [x] Execution endpoint (`POST /api/tests/run`).
- **Frontend Tasks:**
  - [x] Test Runner controls (`frontend/src/components/TestRunnerPanel.tsx`): Select test target or run regression tests.
  - [x] Terminal captured output panel with clear status badges (`VERIFIED PASSED`, `TESTS FAILED`, `TIMEOUT EXCEEDED`, `EXECUTION ERROR`).
  - [x] Honest status indicator: clear separation between "Tests not yet run", "Running", "Failed", and "Verified".
- **Verification & Acceptance Criteria:**
  - [x] Test runner security tests (disallow traversal and arbitrary bash commands) (`backend/tests/test_runner.py`).
  - [x] Timeout and exit code capture verified with simulated hanging tests.


### Phase 5: Bounded Repair Loop & Audit Trail
- **Objective:** If tests fail, feed exact failure evidence back into model for a bounded retry (max 2 attempts) with approval at each step.
- **Backend Tasks:**
  - [x] Failure evidence extractor (grabs pytest traceback and failed assertions).
  - [x] Repair loop orchestrator: bounds iterations (default 2), tracks patch versions (v1, v2) (`backend/app/repair.py`).
  - [x] Final Verification Report generator: JSON & Markdown export with full audit history.
  - [x] Endpoints: `POST /api/repair/start`, `POST /api/repair/{id}/iterate`, `GET /api/repair/{id}/report`.
- **Frontend Tasks:**
  - [x] Iteration timeline showing v1 -> Test Result -> v2 -> Verification (`frontend/src/components/RepairAuditPanel.tsx`).
  - [x] Final Verification Report view with one-click Markdown export.
  - [x] Audit trail table displaying timestamps, event types, and serialized execution payloads.
- **Verification & Acceptance Criteria:**
  - [x] Unit tests verify loop strictly halts at max limit (`backend/tests/test_repair.py`).
  - [x] Audit trail contains timestamps, diffs, commands, and stdout/stderr.


### Phase 6: Benchmark Suite, Quality & Release
- **Objective:** Reproducible synthetic test repository with known bugs, comprehensive documentation, and end-to-end evaluation.
- **Deliverables:**
  - [x] Synthetic test benchmark repository (`benchmarks/sample_repo`).
  - [x] Comprehensive documentation:
    - [x] `README.md` (Setup, architecture, demo run)
    - [x] `docs/ARCHITECTURE.md` (Mermaid diagrams, subsystem breakdowns)
    - [x] `docs/LEARNING_GUIDE.md` (Educational guide for interviews)
    - [x] `docs/API_REFERENCE.md` (OpenAPI REST documentation)
    - [x] `docs/SECURITY.md` (Defensive design & sandbox policy)
    - [x] `docs/DECISIONS.md` (Architecture Decision Records)
  - [x] End-to-end evaluation run report with actual measured metrics (`19/19 backend tests passed`, clean frontend Vite build).

