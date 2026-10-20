"""
Tests for Controlled Test Runner & Security Boundaries (Phase 4).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, REPO_REGISTRY


client = TestClient(app)


def test_run_tests_on_sample_repo_exposes_bug():
    """Verify test runner accurately executes pytest and captures failures and traceback."""
    sample_path = str(Path(__file__).parents[2] / "benchmarks" / "sample_repo")
    reg_resp = client.post("/api/repositories", json={"path": sample_path})
    assert reg_resp.status_code == 200
    repo_id = reg_resp.json()["repo_id"]

    run_req = {
        "repo_id": repo_id,
        "test_target": "test_expense.py",
        "timeout_seconds": 15,
    }
    resp = client.post("/api/tests/run", json=run_req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "failed"
    assert data["exit_code"] == 1
    assert data["passed_count"] == 3
    assert data["failed_count"] == 1
    assert data["failure_traceback"] is not None
    assert "ZeroDivisionError" in data["failure_traceback"]


def test_security_disallows_path_traversal():
    """Verify path traversal attempts are blocked by security check."""
    sample_path = str(Path(__file__).parents[2] / "benchmarks" / "sample_repo")
    reg_resp = client.post("/api/repositories", json={"path": sample_path})
    assert reg_resp.status_code == 200
    repo_id = reg_resp.json()["repo_id"]

    # Traversal attempt with ../
    run_req = {
        "repo_id": repo_id,
        "test_target": "../../backend/tests/test_repository.py",
    }
    resp = client.post("/api/tests/run", json=run_req)
    assert resp.status_code == 403
    assert "traversal" in resp.json()["detail"].lower()

    # Traversal attempt with Windows-style backslashes
    run_req_win = {
        "repo_id": repo_id,
        "test_target": "..\\..\\sensitive.py",
    }
    resp_win = client.post("/api/tests/run", json=run_req_win)
    assert resp_win.status_code == 403
    assert "traversal" in resp_win.json()["detail"].lower()


def test_test_runner_timeout_handling(tmp_path):
    """Verify infinite loop or hanging test gets killed upon timeout."""
    hanging_test = (
        "import time\n"
        "def test_hang():\n"
        "    time.sleep(10)\n"
    )
    test_dir = tmp_path / "hang_repo"
    test_dir.mkdir()
    (test_dir / "test_hang.py").write_text(hanging_test, encoding="utf-8")

    reg_resp = client.post("/api/repositories", json={"path": str(test_dir)})
    assert reg_resp.status_code == 200
    repo_id = reg_resp.json()["repo_id"]

    run_req = {
        "repo_id": repo_id,
        "test_target": "test_hang.py",
        "timeout_seconds": 1,  # Strict 1s timeout
    }
    resp = client.post("/api/tests/run", json=run_req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "timeout"
    assert "exceeded" in data["stderr"].lower() or "timeout" in data["failure_traceback"].lower()
