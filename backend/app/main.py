"""
FastAPI application router and entrypoint for RepoPilot.
Provides endpoints for repository management, file tree exploration,
source preview with line numbers, and lexical search.
"""

from pathlib import Path
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.security import SecurityException
from app.repository import (
    detect_repo_metadata,
    get_file_tree,
    read_file_safe,
    search_repo_lexical,
    RepoMetadata,
)
from app.schemas import (
    RegisterRepoRequest,
    RepoInfoResponse,
    FileContentResponse,
    SearchResponse,
    SearchResultItem,
    InvestigationRequest,
    InvestigationResponse,
    SystemStatusResponse,
    GeneratePatchRequest,
    PatchProposalResponse,
    PatchActionRequest,
    RunTestRequest,
    TestExecutionResponse,
    RepairSessionResponse,
    VerificationReportResponse,
)
from app.llm import OllamaProvider
from app.investigator import InvestigationEngine
from app.patcher import PatchEngine, PatchValidationException
from app.runner import TestRunner, SecurityViolation
from app.repair import RepairLoopOrchestrator

app = FastAPI(
    title="RepoPilot API",
    description="Backend API for RepoPilot AI Software Engineering Agent",
    version="0.1.0",
)

# Initialize engines
ollama_provider = OllamaProvider()
investigation_engine = InvestigationEngine(provider=ollama_provider)
patch_engine = PatchEngine(provider=ollama_provider)
test_runner = TestRunner()
repair_orchestrator = RepairLoopOrchestrator(
    patch_engine=patch_engine,
    test_runner=test_runner,
    provider=ollama_provider,
)





# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory registry for repositories (in Phase 1)
# Stored as repo_id -> RepoMetadata
REPO_REGISTRY: Dict[str, RepoMetadata] = {}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "RepoPilot", "version": "0.1.0"}


@app.get("/api/system/status", response_model=SystemStatusResponse)
def get_system_status():
    """
    Check availability of local LLM engine (Ollama) and installed models.
    """
    is_up = ollama_provider.is_available()
    models = ollama_provider.list_models() if is_up else []
    return SystemStatusResponse(
        status="operational" if is_up else "degraded",
        ollama_online=is_up,
        models=models,
        active_model=ollama_provider.default_model,
    )


@app.post("/api/investigate", response_model=InvestigationResponse)
def investigate_bug(req: InvestigationRequest):
    """
    Model-assisted bug investigation with grounded code evidence.
    """
    if req.repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[req.repo_id]
    try:
        diagnosis = investigation_engine.investigate(Path(repo.root_path), req)
        return diagnosis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


@app.post("/api/patches/generate", response_model=PatchProposalResponse)
def generate_patch(req: GeneratePatchRequest):
    """
    Generate minimal unified diff and register pending patch proposal.
    """
    if req.repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[req.repo_id]
    try:
        proposal = patch_engine.generate_patch(Path(repo.root_path), req)
        return proposal
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate patch: {str(e)}")


@app.get("/api/patches/{patch_id}", response_model=PatchProposalResponse)
def get_patch(patch_id: str):
    """
    Get patch proposal by ID.
    """
    proposal = patch_engine.get_patch(patch_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Patch not found: {patch_id}")
    return proposal


@app.post("/api/patches/{patch_id}/approve", response_model=PatchProposalResponse)
def approve_patch(patch_id: str):
    """
    Explicitly approve and apply a patch to the repository source code.
    """
    proposal = patch_engine.get_patch(patch_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Patch not found: {patch_id}")

    if proposal.repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Associated repository not found")

    repo = REPO_REGISTRY[proposal.repo_id]
    try:
        updated = patch_engine.approve_and_apply_patch(Path(repo.root_path), patch_id)
        return updated
    except PatchValidationException as pve:
        raise HTTPException(status_code=400, detail=str(pve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply patch: {str(e)}")


@app.post("/api/patches/{patch_id}/reject", response_model=PatchProposalResponse)
def reject_patch(patch_id: str, action: Optional[PatchActionRequest] = None):
    """
    Explicitly reject a patch. Ensures no code is touched.
    """
    proposal = patch_engine.get_patch(patch_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Patch not found: {patch_id}")

    reason = action.reason if action else None
    return patch_engine.reject_patch(patch_id, reason=reason)


@app.post("/api/tests/run", response_model=TestExecutionResponse)
def run_tests(req: RunTestRequest):
    """
    Controlled test runner executing allowlisted pytest within strict isolation bounds.
    """
    if req.repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[req.repo_id]
    try:
        result = test_runner.execute_test(Path(repo.root_path), req)
        return result
    except SecurityViolation as sv:
        raise HTTPException(status_code=403, detail=str(sv))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test runner error: {str(e)}")


@app.post("/api/repair/start", response_model=RepairSessionResponse)
def start_repair_session(
    repo_id: str,
    target_file: str,
    issue_description: str,
    root_cause: str,
    test_target: str = "test_expense.py",
    max_iterations: int = 2,
):
    """
    Start a bounded repair session (max iterations default 2).
    """
    if repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[repo_id]
    session = repair_orchestrator.start_repair_session(
        repo_root=Path(repo.root_path),
        repo_id=repo_id,
        repo_name=repo.name,
        target_file=target_file,
        issue_description=issue_description,
        root_cause=root_cause,
        test_target=test_target,
        max_iterations=max_iterations,
    )
    return repair_orchestrator._session_to_response(session)


@app.post("/api/repair/{session_id}/iterate", response_model=RepairSessionResponse)
def execute_repair_iteration(session_id: str, feedback: Optional[str] = None):
    """
    Execute next bounded repair iteration.
    """
    if session_id not in repair_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Repair session not found")

    session = repair_orchestrator.sessions[session_id]
    if session.repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Associated repository not found")

    repo = REPO_REGISTRY[session.repo_id]
    try:
        response = repair_orchestrator.execute_bounded_iteration(
            repo_root=Path(repo.root_path),
            session_id=session_id,
            feedback=feedback,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair iteration failed: {str(e)}")


@app.get("/api/repair/{session_id}/report", response_model=VerificationReportResponse)
def get_verification_report(session_id: str):
    """
    Generate and export audited Verification Report in JSON and Markdown.
    """
    if session_id not in repair_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Repair session not found")

    try:
        return repair_orchestrator.generate_verification_report(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")






@app.post("/api/repositories", response_model=RepoInfoResponse)
def register_repository(req: RegisterRepoRequest):
    """
    Validate and register a local repository directory.
    """
    resolved_path = Path(req.path).resolve()
    if not resolved_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {req.path}")
    if not resolved_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {req.path}")

    # Check if already registered
    for repo_id, meta in REPO_REGISTRY.items():
        if Path(meta.root_path) == resolved_path:
            return RepoInfoResponse(
                repo_id=meta.repo_id,
                name=meta.name,
                root_path=meta.root_path,
                manifest_type=meta.manifest_type,
                has_git=meta.has_git,
                test_framework=meta.test_framework,
            )

    repo_id = str(uuid.uuid4())[:8]
    try:
        metadata = detect_repo_metadata(resolved_path, repo_id)
        REPO_REGISTRY[repo_id] = metadata
        return RepoInfoResponse(
            repo_id=metadata.repo_id,
            name=metadata.name,
            root_path=metadata.root_path,
            manifest_type=metadata.manifest_type,
            has_git=metadata.has_git,
            test_framework=metadata.test_framework,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect repository: {str(e)}")


@app.get("/api/repositories", response_model=List[RepoInfoResponse])
def list_repositories():
    """
    List all currently registered repositories.
    """
    return [
        RepoInfoResponse(
            repo_id=meta.repo_id,
            name=meta.name,
            root_path=meta.root_path,
            manifest_type=meta.manifest_type,
            has_git=meta.has_git,
            test_framework=meta.test_framework,
        )
        for meta in REPO_REGISTRY.values()
    ]


@app.get("/api/repositories/{repo_id}/tree")
def get_repository_tree(repo_id: str, max_depth: int = Query(6, ge=1, le=10)):
    """
    Get safe hierarchical file tree for the repository.
    """
    if repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[repo_id]
    tree = get_file_tree(repo.root_path, max_depth=max_depth)
    return tree.to_dict()


@app.get("/api/repositories/{repo_id}/files", response_model=FileContentResponse)
def get_file_contents(
    repo_id: str,
    path: str = Query(..., description="Relative path within the repository"),
    start: Optional[int] = Query(None, ge=1, description="1-indexed starting line"),
    end: Optional[int] = Query(None, ge=1, description="1-indexed ending line"),
):
    """
    Safely read source content with line numbers and bounds checks.
    """
    if repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[repo_id]
    try:
        data = read_file_safe(repo.root_path, path, start_line=start, end_line=end)
        return FileContentResponse(**data)
    except SecurityException as se:
        raise HTTPException(status_code=403, detail=str(se))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/repositories/{repo_id}/search", response_model=SearchResponse)
def search_repository(
    repo_id: str,
    q: str = Query(..., min_length=1, description="Search query string"),
    max_results: int = Query(50, ge=1, le=200),
):
    """
    Perform lexical code search across repository source files.
    """
    if repo_id not in REPO_REGISTRY:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = REPO_REGISTRY[repo_id]
    raw_results = search_repo_lexical(repo.root_path, query=q, max_results=max_results)
    results = [
        SearchResultItem(
            file_path=r["file_path"],
            line_number=r["line_number"],
            line_content=r["line_content"],
        )
        for r in raw_results
    ]
    return SearchResponse(query=q, total_results=len(results), results=results)
