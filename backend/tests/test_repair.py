"""
Tests for Bounded Repair Loop and Audit Trail (Phase 5).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, REPO_REGISTRY, patch_engine
from app.llm import MockLLMProvider


client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_repair_llm():
    mock_provider = MockLLMProvider()
    patch_engine.set_provider(mock_provider)
    yield mock_provider


@pytest.fixture
def disposable_repo(tmp_path):
    repo_dir = tmp_path / "repair_repo"
    repo_dir.mkdir()
    expense_code = (
        'def calculate_expense_share(total_amount: float, participant_count: int) -> float:\n'
        '    if total_amount < 0:\n'
        '        raise ValueError("Total amount cannot be negative")\n'
        '    # Missing zero check!\n'
        '    return total_amount / participant_count\n'
    )
    test_code = (
        'import pytest\n'
        'from expense import calculate_expense_share\n\n'
        'def test_zero_share():\n'
        '    with pytest.raises(ValueError):\n'
        '        calculate_expense_share(100.0, 0)\n'
    )
    (repo_dir / "expense.py").write_text(expense_code, encoding="utf-8")
    (repo_dir / "test_expense.py").write_text(test_code, encoding="utf-8")

    resp = client.post("/api/repositories", json={"path": str(repo_dir)})
    assert resp.status_code == 200
    repo_id = resp.json()["repo_id"]
    return repo_dir, repo_id


def test_bounded_repair_loop_success_and_audit(disposable_repo):
    repo_dir, repo_id = disposable_repo

    # 1. Start bounded repair session
    params = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share raises ZeroDivisionError on 0",
        "root_cause": "Missing zero check before division",
        "test_target": "test_expense.py",
        "max_iterations": 2,
    }
    resp = client.post("/api/repair/start", params=params)
    assert resp.status_code == 200
    session_data = resp.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "in_progress"
    assert session_data["max_iterations"] == 2
    assert session_data["current_iteration"] == 0

    # 2. Execute bounded iteration 1
    it1_resp = client.post(f"/api/repair/{session_id}/iterate")
    assert it1_resp.status_code == 200
    it1_data = it1_resp.json()
    assert it1_data["current_iteration"] == 1
    assert it1_data["status"] == "verified"  # Mock provider generates fix that satisfies test_expense.py

    # Verify that during candidate testing, original repository file remained completely untouched!
    original_code_still = (repo_dir / "expense.py").read_text(encoding="utf-8")
    assert "Missing zero check!" in original_code_still
    assert "participant_count <= 0" not in original_code_still

    # 3. Request Verification Report
    report_resp = client.get(f"/api/repair/{session_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert report["tests_verified"] is True
    assert report["iterations_taken"] == 1
    assert len(report["audit_events"]) >= 3
    assert "# RepoPilot Verification & Audit Report" in report["markdown_report"]
    assert "✅ PASSED" in report["markdown_report"]

    # 4. Explicitly apply the verified patch and verify original repository is now updated
    apply_resp = client.post(f"/api/repair/{session_id}/apply")
    assert apply_resp.status_code == 200
    assert apply_resp.json()["status"] == "applied"

    updated_code = (repo_dir / "expense.py").read_text(encoding="utf-8")
    assert "participant_count <= 0" in updated_code


def test_rejected_patch_preserves_original_source(disposable_repo):
    repo_dir, repo_id = disposable_repo
    original_code = (repo_dir / "expense.py").read_text(encoding="utf-8")

    # Generate patch
    req = {
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "calculate_expense_share crashes on zero",
        "suggested_fix": "Add check for participant_count <= 0",
    }
    gen_resp = client.post("/api/patches/generate", json=req)
    patch_id = gen_resp.json()["patch_id"]

    # Reject patch
    rej_resp = client.post(f"/api/patches/{patch_id}/reject", json={"patch_id": patch_id, "reason": "User rejected"})
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # Source code must remain completely untouched
    assert (repo_dir / "expense.py").read_text(encoding="utf-8") == original_code


def test_failed_patch_application_safety(disposable_repo):
    repo_dir, repo_id = disposable_repo
    original_code = (repo_dir / "expense.py").read_text(encoding="utf-8")

    # Modifying file externally causes conflict on approve
    gen_resp = client.post("/api/patches/generate", json={
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "zero division",
        "suggested_fix": "check <= 0",
    })
    patch_id = gen_resp.json()["patch_id"]

    # External modification
    (repo_dir / "expense.py").write_text(original_code + "\n# external change\n", encoding="utf-8")

    # Approval should fail due to conflict and leave external file intact without corrupting
    app_resp = client.post(f"/api/patches/{patch_id}/approve")
    assert app_resp.status_code == 400
    assert "conflict" in app_resp.json()["detail"].lower()
    assert (repo_dir / "expense.py").read_text(encoding="utf-8") == original_code + "\n# external change\n"


def test_repair_loop_halts_strictly_at_max_iterations(tmp_path):
    repo_dir = tmp_path / "fail_repo"
    repo_dir.mkdir()
    (repo_dir / "expense.py").write_text("x = 1\n", encoding="utf-8")
    # Always failing test
    (repo_dir / "test_always_fail.py").write_text("def test_fail(): assert False\n", encoding="utf-8")

    resp = client.post("/api/repositories", json={"path": str(repo_dir)})
    repo_id = resp.json()["repo_id"]

    start_resp = client.post("/api/repair/start", params={
        "repo_id": repo_id,
        "target_file": "expense.py",
        "issue_description": "test issue",
        "root_cause": "test cause",
        "test_target": "test_always_fail.py",
        "max_iterations": 2,
    })
    session_id = start_resp.json()["session_id"]

    # Iteration 1
    it1 = client.post(f"/api/repair/{session_id}/iterate").json()
    assert it1["current_iteration"] == 1
    assert it1["status"] == "in_progress"

    # Iteration 2 (Max reached)
    it2 = client.post(f"/api/repair/{session_id}/iterate").json()
    assert it2["current_iteration"] == 2
    assert it2["status"] == "max_iterations_reached"

    # Attempting iteration 3 MUST halt without incrementing
    it3 = client.post(f"/api/repair/{session_id}/iterate").json()
    assert it3["current_iteration"] == 2
    assert it3["status"] == "max_iterations_reached"
    assert "Terminated" in it3["final_verdict"]
