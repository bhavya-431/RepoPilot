import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app, REPO_REGISTRY
from app.security import resolve_safe_path, SecurityException
from app.repository import detect_repo_metadata, get_file_tree, read_file_safe, search_repo_lexical

client = TestClient(app)

SAMPLE_REPO_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "sample_repo"


def test_security_path_traversal_detection():
    # Trying to escape SAMPLE_REPO_DIR
    with pytest.raises(SecurityException):
        resolve_safe_path(SAMPLE_REPO_DIR, "../../../Windows/System32/drivers/etc/hosts")

    with pytest.raises(SecurityException):
        resolve_safe_path(SAMPLE_REPO_DIR, "..\\..\\sensitive.txt")


def test_security_valid_path():
    valid = resolve_safe_path(SAMPLE_REPO_DIR, "expense.py")
    assert valid.exists()
    assert valid.name == "expense.py"


def test_repo_metadata_detection():
    meta = detect_repo_metadata(SAMPLE_REPO_DIR, "test-123")
    assert meta.repo_id == "test-123"
    assert meta.name == "sample_repo"
    assert meta.test_framework == "pytest" or meta.test_framework is None


def test_file_tree():
    tree = get_file_tree(SAMPLE_REPO_DIR)
    assert tree.is_dir is True
    file_names = [child.name for child in tree.children]
    assert "expense.py" in file_names
    assert "test_expense.py" in file_names


def test_read_file_safe():
    data = read_file_safe(SAMPLE_REPO_DIR, "expense.py", start_line=1, end_line=10)
    assert data["file_path"] == "expense.py"
    assert len(data["lines"]) == 10
    assert data["lines"][0]["line_number"] == 1
    assert "calculate_expense_share" in data["raw_text"]


def test_lexical_search():
    results = search_repo_lexical(SAMPLE_REPO_DIR, "calculate_expense_share")
    assert len(results) >= 2  # Definition in expense.py, usage in test_expense.py
    file_paths = [r["file_path"] for r in results]
    assert "expense.py" in file_paths
    assert "test_expense.py" in file_paths


def test_api_register_and_explore():
    REPO_REGISTRY.clear()
    # 1. Register
    resp = client.post("/api/repositories", json={"path": str(SAMPLE_REPO_DIR)})
    assert resp.status_code == 200
    repo_data = resp.json()
    repo_id = repo_data["repo_id"]
    assert repo_data["name"] == "sample_repo"

    # 2. Get tree
    resp_tree = client.get(f"/api/repositories/{repo_id}/tree")
    assert resp_tree.status_code == 200
    assert len(resp_tree.json()["children"]) >= 2

    # 3. Read file
    resp_file = client.get(f"/api/repositories/{repo_id}/files?path=expense.py&start=1&end=15")
    assert resp_file.status_code == 200
    assert resp_file.json()["total_lines"] > 0
    assert len(resp_file.json()["lines"]) <= 15

    # 4. Search
    resp_search = client.get(f"/api/repositories/{repo_id}/search?q=ZeroDivisionError")
    assert resp_search.status_code == 200
    assert resp_search.json()["total_results"] >= 1
    found_files = [r["file_path"] for r in resp_search.json()["results"]]
    assert "expense.py" in found_files or "test_expense.py" in found_files

    # 5. Path traversal attempt via API
    resp_bad = client.get(f"/api/repositories/{repo_id}/files?path=../../outside.txt")
    assert resp_bad.status_code == 403
