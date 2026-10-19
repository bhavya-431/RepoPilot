"""
Tests for OllamaProvider error handling, response validation, truncation checks, and MockLLMProvider compatibility.
"""

import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from app.llm import OllamaProvider, MockLLMProvider, LLMException


def test_ollama_valid_response():
    """Verify OllamaProvider handles normal valid completions."""
    provider = OllamaProvider(timeout=5, options={"num_predict": 128})
    mock_payload = {
        "done": True,
        "done_reason": "stop",
        "eval_count": 42,
        "prompt_eval_count": 10,
        "response": '{"explanation": "Valid test fix", "repaired_content": "def foo(): pass"}',
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = provider.generate("Fix the bug")
        assert res == mock_payload["response"]


def test_ollama_empty_response():
    """Verify OllamaProvider raises LLMException when response text is empty."""
    provider = OllamaProvider(timeout=5)
    mock_payload = {
        "done": True,
        "done_reason": "stop",
        "eval_count": 0,
        "response": "   ",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(LLMException) as exc_info:
            provider.generate("Fix the bug")
        assert "empty response" in str(exc_info.value)


def test_ollama_truncated_response_length():
    """Verify OllamaProvider raises LLMException when done_reason == 'length'."""
    provider = OllamaProvider(timeout=5, options={"num_predict": 256})
    mock_payload = {
        "done": True,
        "done_reason": "length",
        "eval_count": 256,
        "response": '{"explanation": "Partial answer that got cut off...',
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(LLMException) as exc_info:
            provider.generate("Fix the bug")
        assert "truncated because the token limit was reached" in str(exc_info.value)
        assert "done_reason='length'" in str(exc_info.value)


def test_ollama_connection_timeout():
    """Verify OllamaProvider converts timeout URLError into LLMException."""
    provider = OllamaProvider(timeout=1)

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        with pytest.raises(LLMException) as exc_info:
            provider.generate("Fix the bug")
        assert "Failed to connect to Ollama" in str(exc_info.value)
        assert "timed out" in str(exc_info.value)


def test_mock_llm_provider_compatibility():
    """Verify MockLLMProvider continues to work seamlessly across investigation and patch generation."""
    mock = MockLLMProvider()
    assert mock.is_available() is True
    assert mock.get_provider_name() == "mock:mock-model"
    assert mock.get_execution_mode() == "mock"
    assert "mock-model" in mock.list_models()

    # Normal investigation prompt
    res = mock.generate("Investigate bug")
    data = json.loads(res)
    assert "root_cause" in data
    assert "evidence" in data

    # Patch prompt
    patch_res = mock.generate("Produce repaired_content for TARGET FILE expense.py")
    patch_data = json.loads(patch_res)
    assert "repaired_content" in patch_data
    assert "ExpenseTracker" not in patch_data or "calculate_expense_share" in patch_data["repaired_content"]
