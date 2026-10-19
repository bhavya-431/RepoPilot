# REST API Reference — RepoPilot

RepoPilot backend runs by default on `http://localhost:8000`.  
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 1. System & Health

### `GET /api/health`
Basic service health check.
- **Response:**
  ```json
  { "status": "ok", "app": "RepoPilot", "version": "0.1.0" }
  ```

### `GET /api/system/status`
Queries the status of the local LLM daemon (Ollama) and lists installed models.
- **Response Model:** `SystemStatusResponse`
  ```json
  {
    "status": "operational",
    "ollama_online": true,
    "models": ["gemma4:latest"],
    "active_model": "gemma4:latest"
  }
  ```

---

## 2. Repository Management

### `POST /api/repositories`
Registers and inspects a local repository folder.
- **Request Body:**
  ```json
  { "path": "benchmarks/sample_repo" }
  ```
- **Response Model:** `RepoInfoResponse`
  ```json
  {
    "repo_id": "b3f81e2a",
    "name": "sample_repo",
    "root_path": "C:\\Users\\...\\benchmarks\\sample_repo",
    "manifest_type": "python",
    "has_git": true,
    "test_framework": "pytest"
  }
  ```

### `GET /api/repositories`
Lists all registered repositories.

### `GET /api/repositories/{repo_id}/tree`
Returns the hierarchical file tree up to `max_depth` (default 6).
- **Query Params:** `max_depth: int`
- **Exclusions:** `.git`, `.venv`, `node_modules`, `__pycache__`

### `GET /api/repositories/{repo_id}/files`
Safely reads file lines with bounds checks and line numbers.
- **Query Params:** `path: str`, `start: Optional[int]`, `end: Optional[int]`
- **Response Model:** `FileContentResponse`

### `GET /api/repositories/{repo_id}/search`
Executes fast lexical search across repository source files.
- **Query Params:** `q: str`, `max_results: int = 50`
- **Response Model:** `SearchResponse`

---

## 3. Bug Investigation

### `POST /api/investigate`
Performs model-assisted bug diagnosis grounded in code evidence.
- **Request Body:**
  ```json
  {
    "repo_id": "b3f81e2a",
    "issue_description": "calculate_expense_share crashes on zero participants",
    "traceback": "File \"expense.py\", line 14, in calculate_expense_share...",
    "target_files": ["expense.py"]
  }
  ```
- **Response Model:** `InvestigationResponse`
  ```json
  {
    "investigation_id": "inv-9a4f21d3",
    "repo_id": "b3f81e2a",
    "status": "completed",
    "root_cause": "Division by zero when participant count is 0",
    "evidence": [
      {
        "file_path": "expense.py",
        "start_line": 13,
        "end_line": 15,
        "snippet": "return total_amount / participant_count",
        "explanation": "No validation performed to verify participant_count > 0"
      }
    ],
    "suggested_fix": "Add validation for participant_count <= 0",
    "recommended_test": "test_calculate_share_zero_participants",
    "confidence": 0.95
  }
  ```

---

## 4. Patch Generation & Review

### `POST /api/patches/generate`
Synthesizes a minimal unified diff and registers a pending patch proposal.
- **Request Body:** `GeneratePatchRequest`
- **Response Model:** `PatchProposalResponse`

### `GET /api/patches/{patch_id}`
Retrieves a patch proposal and unified diff by ID.

### `POST /api/patches/{patch_id}/approve`
Explicitly approves and applies the patch to the target source file after conflict validation.

### `POST /api/patches/{patch_id}/reject`
Explicitly rejects the patch proposal. Source files remain untouched.

---

## 5. Controlled Test Runner

### `POST /api/tests/run`
Executes allowlisted pytest in an isolated subprocess with timeout and output capture.
- **Request Body:**
  ```json
  {
    "repo_id": "b3f81e2a",
    "test_target": "test_expense.py",
    "timeout_seconds": 30
  }
  ```
- **Response Model:** `TestExecutionResponse`
  ```json
  {
    "execution_id": "test-3f2d1e8c",
    "repo_id": "b3f81e2a",
    "command": "python -m pytest test_expense.py",
    "status": "passed",
    "exit_code": 0,
    "passed_count": 4,
    "failed_count": 0,
    "error_count": 0,
    "duration_seconds": 0.45,
    "stdout": "...",
    "stderr": "",
    "failure_traceback": null
  }
  ```

---

## 6. Bounded Repair Loop & Audit Trail

### `POST /api/repair/start`
Starts a bounded repair session (max iterations default 2).
- **Query Params:** `repo_id`, `target_file`, `issue_description`, `root_cause`, `test_target`, `max_iterations`
- **Response Model:** `RepairSessionResponse`

### `POST /api/repair/{session_id}/iterate`
Executes next repair cycle (synthesizes patch, applies, runs tests, checks bounds).
- **Query Params:** `feedback: Optional[str]`
- **Response Model:** `RepairSessionResponse`

### `GET /api/repair/{session_id}/report`
Exports comprehensive Verification Report and immutable audit trail.
- **Response Model:** `VerificationReportResponse`
