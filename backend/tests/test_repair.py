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

    # 3. Request Verification Report
    report_resp = client.get(f"/api/repair/{session_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert report["tests_verified"] is True
    assert report["iterations_taken"] == 1
    assert len(report["audit_events"]) >= 3
    assert "# RepoPilot Verification & Audit Report" in report["markdown_report"]
    assert "✅ PASSED" in report["markdown_report"]


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
