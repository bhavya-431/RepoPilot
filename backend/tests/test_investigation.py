"""
Tests for Bug Investigation Engine and LLM Provider abstraction.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, REPO_REGISTRY, investigation_engine
from app.llm import MockLLMProvider
from app.investigator import InvestigationEngine
from app.schemas import InvestigationRequest


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_mock_llm():
    """Ensure tests run deterministically with MockLLMProvider without waiting for live inference."""
    mock_provider = MockLLMProvider()
    investigation_engine.set_provider(mock_provider)
    yield mock_provider


def test_system_status():
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ollama_online" in data
    assert "models" in data
    assert "active_model" in data


def test_investigation_endpoint():
    # 1. Register sample_repo
    sample_path = str(Path(__file__).parents[2] / "benchmarks" / "sample_repo")
    reg_resp = client.post("/api/repositories", json={"path": sample_path})
    assert reg_resp.status_code == 200
    repo_id = reg_resp.json()["repo_id"]

    # 2. Trigger investigation
    inv_req = {
        "repo_id": repo_id,
        "issue_description": "calculate_expense_share crashes with ZeroDivisionError when participant count is 0",
        "traceback": 'File "expense.py", line 14, in calculate_expense_share\n  return total_amount / participant_count\nZeroDivisionError: division by zero',
        "target_files": ["expense.py"],
    }
    resp = client.post("/api/investigate", json=inv_req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "completed"
    assert "Division by zero" in data["root_cause"]
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["file_path"] == "expense.py"
    assert "suggested_fix" in data
    assert data["confidence"] > 0.5


def test_investigation_not_found_repo():
    inv_req = {
        "repo_id": "nonexistent-repo-id",
        "issue_description": "test issue",
    }
    resp = client.post("/api/investigate", json=inv_req)
    assert resp.status_code == 404
