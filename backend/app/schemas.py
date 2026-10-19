"""
Pydantic data models for API requests and responses.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegisterRepoRequest(BaseModel):
    path: str = Field(..., description="Local path to repository folder")


class RepoInfoResponse(BaseModel):
    repo_id: str
    name: str
    root_path: str
    manifest_type: Optional[str] = None
    has_git: bool
    test_framework: Optional[str] = None


class FileTreeNodeResponse(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    children: List["FileTreeNodeResponse"] = []


class FileLine(BaseModel):
    line_number: int
    content: str


class FileContentResponse(BaseModel):
    file_path: str
    total_lines: int
    start_line: int
    end_line: int
    lines: List[FileLine]
    raw_text: str


class SearchResultItem(BaseModel):
    file_path: str
    line_number: int
    line_content: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]


class EvidenceCitation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    explanation: str


class InvestigationRequest(BaseModel):
    repo_id: str
    issue_description: str
    traceback: Optional[str] = None
    target_files: Optional[List[str]] = None


class InvestigationResponse(BaseModel):
    investigation_id: str
    repo_id: str
    status: str
    root_cause: str
    evidence: List[EvidenceCitation]
    suggested_fix: str
    recommended_test: Optional[str] = None
    confidence: float
    known_uncertainties: Optional[str] = None
    provider_name: str = "unknown"  # e.g., 'ollama:gemma4:latest', 'mock-model', 'heuristic_fallback'
    execution_mode: str = "model"   # 'live_model', 'deterministic_fallback', 'mock'
    latency_seconds: Optional[float] = None


class SystemStatusResponse(BaseModel):
    status: str
    ollama_online: bool
    models: List[str]
    active_model: str


class GeneratePatchRequest(BaseModel):
    repo_id: str
    target_file: str
    issue_description: str
    suggested_fix: str
    root_cause: Optional[str] = None


class PatchHunk(BaseModel):
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[str]


class PatchFileDiff(BaseModel):
    file_path: str
    diff_text: str
    added_count: int
    removed_count: int
    is_applicable: bool
    validation_error: Optional[str] = None


class PatchProposalResponse(BaseModel):
    patch_id: str
    repo_id: str
    version: str
    target_file: str
    explanation: str
    diff: PatchFileDiff
    status: str  # pending_review, approved, rejected, applied
    provider_name: str = "unknown"  # e.g., 'ollama:gemma4:latest', 'mock-model', 'heuristic_fallback'
    execution_mode: str = "model"   # 'live_model', 'deterministic_fallback', 'mock'
    latency_seconds: Optional[float] = None


class PatchActionRequest(BaseModel):
    patch_id: str
    reason: Optional[str] = None


class RunTestRequest(BaseModel):
    repo_id: str
    test_target: Optional[str] = None  # e.g., 'test_expense.py' or 'tests'
    timeout_seconds: Optional[int] = Field(30, ge=1, le=120)


class TestExecutionResponse(BaseModel):
    execution_id: str
    repo_id: str
    command: str
    status: str  # 'passed', 'failed', 'timeout', 'error'
    exit_code: Optional[int] = None
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    duration_seconds: float = 0.0
    stdout: str
    stderr: str
    failure_traceback: Optional[str] = None


class RepairIteration(BaseModel):
    iteration_number: int
    patch_id: Optional[str] = None
    version: str
    patch_explanation: Optional[str] = None
    test_status: Optional[str] = None
    test_stdout: Optional[str] = None
    failure_traceback: Optional[str] = None
    timestamp: str


class RepairSessionResponse(BaseModel):
    session_id: str
    repo_id: str
    target_file: str
    max_iterations: int
    current_iteration: int
    status: str  # 'in_progress', 'verified', 'max_iterations_reached', 'failed'
    iterations: List[RepairIteration]
    final_verdict: str


class VerificationReportResponse(BaseModel):
    report_id: str
    repo_id: str
    repo_name: str
    session_id: str
    timestamp: str
    status: str
    root_cause: str
    fix_applied: str
    tests_verified: bool
    iterations_taken: int
    audit_events: List[Dict[str, Any]]
    markdown_report: str




