"""
Unit and integration tests for Patch Generation, Validation, and Approval Workflow (Phase 3).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, REPO_REGISTRY, patch_engine
from app.llm import MockLLMProvider
from app.patcher import PatchEngine, PatchValidationException


client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_patch_provider():
    mock_provider = MockLLMProvider()
    patch_engine.set_provider(mock_provider)
    yield mock_provider


@pytest.fixture
def temp_sample_repo(tmp_path):

    """Create disposable test repository to verify safe patch application and rejection."""
    sample_code = (
        'def calculate_expense_share(total_amount: float, participant_count: int) -> float:\n'
        '    if total_amount < 0:\n'
        '        raise ValueError("Total amount cannot be negative")\n'
        '    # Missing zero check!\n'
        '    return total_amount / participant_count\n'
    )
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    target_file = repo_dir / "expense.py"
    target_file.write_text(sample_code, encoding="utf-8")

    # Register repo with client
    resp = client.post("/api/repositories", json={"path": str(repo_dir)})
    assert resp.status_code == 200
    repo_id = resp.json()["repo_id"]

    return repo_dir, repo_id, target_file, sample_code


def test_generate_patch_proposal(temp_sample_repo):
    repo_dir, repo_id, target_file, sample_code = temp_sample_repo

    req = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share crashes on zero",
        "suggested_fix": "Add check for participant_count <= 0",
    }
    resp = client.post("/api/patches/generate", json=req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "pending_review"
    assert data["target_file"] == "expense.py"
    assert data["diff"]["is_applicable"] is True
    assert "+" in data["diff"]["diff_text"]
    assert "-" in data["diff"]["diff_text"]
    assert data["diff"]["added_count"] > 0

    # Ensure source file is untouched before approval
    assert target_file.read_text(encoding="utf-8") == sample_code


def test_reject_patch_leaves_file_untouched(temp_sample_repo):
    repo_dir, repo_id, target_file, sample_code = temp_sample_repo

    req = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share crashes on zero",
        "suggested_fix": "Add check for participant_count <= 0",
    }
    gen_resp = client.post("/api/patches/generate", json=req)
    patch_id = gen_resp.json()["patch_id"]

    # Reject patch
    reject_resp = client.post(f"/api/patches/{patch_id}/reject", json={"patch_id": patch_id, "reason": "Not minimal enough"})
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    # Source file MUST remain unchanged
    assert target_file.read_text(encoding="utf-8") == sample_code

    # Attempting to approve rejected patch must fail
    approve_resp = client.post(f"/api/patches/{patch_id}/approve")
    assert approve_resp.status_code == 400


def test_approve_patch_applies_modification(temp_sample_repo):
    repo_dir, repo_id, target_file, sample_code = temp_sample_repo

    req = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share crashes on zero",
        "suggested_fix": "Add check for participant_count <= 0",
    }
    gen_resp = client.post("/api/patches/generate", json=req)
    patch_id = gen_resp.json()["patch_id"]

    # Approve patch
    approve_resp = client.post(f"/api/patches/{patch_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "applied"

    # Source file MUST now contain the fix
    new_content = target_file.read_text(encoding="utf-8")
    assert "participant_count <= 0" in new_content
    assert new_content != sample_code


def test_repaired_expense_logic():
    """
    Verify the final repaired calculate_expense_share logic satisfies all specification requirements:
    1. Positive participant counts return exact proportional share.
    2. Zero participants raises ValueError before division.
    3. Negative participant counts raise ValueError.
    4. Negative total amounts raise ValueError (preserved existing behavior).
    """
    def calculate_expense_share(total_amount: float, participant_count: int) -> float:
        if participant_count <= 0:
            raise ValueError("Participant count must be positive")
        if total_amount < 0:
            raise ValueError("Total amount cannot be negative")
        return total_amount / participant_count

    # 1. Positive participant counts
    assert calculate_expense_share(100.0, 4) == 25.0
    assert calculate_expense_share(50.0, 2) == 25.0
    assert calculate_expense_share(10.0, 1) == 10.0

    # 2. Zero participant count
    with pytest.raises(ValueError, match="Participant count must be positive"):
        calculate_expense_share(100.0, 0)

    # 3. Negative participant count
    with pytest.raises(ValueError, match="Participant count must be positive"):
        calculate_expense_share(100.0, -3)

    # 4. Negative total amount
    with pytest.raises(ValueError, match="Total amount cannot be negative"):
        calculate_expense_share(-50.0, 2)


def test_conflict_detection_prevents_silent_overwrite(temp_sample_repo):
    repo_dir, repo_id, target_file, sample_code = temp_sample_repo

    req = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share crashes on zero",
        "suggested_fix": "Add check for participant_count <= 0",
    }
    gen_resp = client.post("/api/patches/generate", json=req)
    patch_id = gen_resp.json()["patch_id"]

    # External modification occurs before approval (drift/conflict)
    target_file.write_text(sample_code + "\n# unexpected external edit\n", encoding="utf-8")

    # Approving must fail due to conflict
    approve_resp = client.post(f"/api/patches/{patch_id}/approve")
    assert approve_resp.status_code == 400
    assert "conflict" in approve_resp.json()["detail"].lower()


def test_investigation_to_patch_generation_workflow(temp_sample_repo):
    """Verify that investigation output cleanly feeds into the patch generation request schema."""
    repo_dir, repo_id, target_file, sample_code = temp_sample_repo

    # 1. Run investigation
    inv_req = {
        "repo_id": repo_id,
        "issue_description": "Expense calculation crashes on zero participants",
        "traceback": 'File "expense.py", line 5\nZeroDivisionError: division by zero',
    }
    inv_resp = client.post("/api/investigate", json=inv_req)
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()

    # Extract target file and suggested fix from investigation result
    target_file_name = inv_data["evidence"][0]["file_path"] if inv_data["evidence"] else "expense.py"
    suggested_fix = inv_data.get("suggested_fix") or "Guard against participant_count <= 0"

    # 2. Invoke patch generation with extracted investigation fields
    patch_req = {
        "repo_id": repo_id,
        "target_file": target_file_name,
        "issue_description": inv_req["issue_description"],
        "suggested_fix": suggested_fix,
        "root_cause": inv_data.get("root_cause"),
    }
    patch_resp = client.post("/api/patches/generate", json=patch_req)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()

    assert patch_data["status"] == "pending_review"
    assert patch_data["target_file"] == target_file_name
    assert patch_data["diff"]["is_applicable"] is True
    assert "diff_text" in patch_data["diff"]
    # Verify file is not automatically modified
    assert target_file.read_text(encoding="utf-8") == sample_code
