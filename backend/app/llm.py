"""
LLM Provider Abstraction for RepoPilot.
Supports Ollama (default local engine, free & private) and MockProvider (deterministic tests).
"""

from abc import ABC, abstractmethod
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMException(Exception):
    pass


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, format: Optional[str] = None) -> str:
        """Generate text completion from the model."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider daemon / server is reachable."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the specific provider/model descriptor."""
        pass

    @abstractmethod
    def get_execution_mode(self) -> str:
        """Returns 'live_model' or 'mock'."""
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "gemma4:latest",
        timeout: int = 120,
        options: Optional[Dict[str, Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        # Default generation options: low temperature for determinism, configurable num_predict
        default_opts: Dict[str, Any] = {
            "temperature": 0.1,
            "num_predict": 512,
        }
        if options:
            default_opts.update(options)
        self.default_options = default_opts

    def get_provider_name(self) -> str:
        return f"ollama:{self.default_model}"

    def get_execution_mode(self) -> str:
        return "live_model"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "RepoPilot"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "RepoPilot"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return models
        except Exception as e:
            logger.warning(f"Failed to query Ollama models: {e}")
            return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        format: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        selected_model = model or self.default_model
        gen_options = dict(self.default_options)
        if options:
            gen_options.update(options)

        payload: Dict[str, Any] = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": gen_options,
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "RepoPilot"},
            method="POST",
        )

        import time
        start_time = time.time()
        prompt_char_len = len(prompt)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                result = json.loads(raw_bytes.decode("utf-8"))
        except urllib.error.URLError as e:
            elapsed = round(time.time() - start_time, 2)
            logger.warning(f"Ollama connection error after {elapsed}s to {self.base_url}: {e}")
            raise LLMException(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.warning(f"Ollama generation error after {elapsed}s: {e}")
            raise LLMException(f"Error generating LLM response: {e}")

        elapsed = round(time.time() - start_time, 2)
        done = result.get("done", False)
        done_reason = result.get("done_reason")
        eval_count = result.get("eval_count", 0)
        prompt_eval_count = result.get("prompt_eval_count", 0)
        response_text = result.get("response", "")

        # Diagnostic metadata logging (no full code or prompt contents logged)
        logger.info(
            f"Ollama response received: model={selected_model}, elapsed={elapsed}s, "
            f"prompt_chars={prompt_char_len}, prompt_tokens={prompt_eval_count}, "
            f"eval_count={eval_count}, done={done}, done_reason={done_reason}"
        )

        if not response_text or not response_text.strip():
            raise LLMException(
                f"Ollama returned an empty response (done={done}, done_reason={done_reason}, eval_count={eval_count})"
            )

        if done_reason == "length":
            raise LLMException(
                f"Ollama output was truncated because the token limit was reached (done_reason='length', eval_count={eval_count}, num_predict={gen_options.get('num_predict')}). Increase num_predict or simplify prompt."
            )

        return response_text


class MockLLMProvider(BaseLLMProvider):
    """Deterministic provider for testing and fallback."""
    def __init__(self, canned_response: Optional[str] = None):
        self.canned_response = canned_response or json.dumps({
            "root_cause": "Division by zero when participant count is 0 in calculate_expense_share",
            "evidence": [
                {
                    "file_path": "expense.py",
                    "start_line": 13,
                    "end_line": 15,
                    "snippet": "return total_amount / participant_count",
                    "explanation": "No validation is performed to verify participant_count > 0 prior to division."
                }
            ],
            "suggested_fix": "Add `if participant_count <= 0: raise ValueError('Participant count must be greater than zero')`.",
            "recommended_test": "test_calculate_share_zero_participants in test_expense.py",
            "confidence": 0.95,
            "known_uncertainties": "Need to confirm whether 0 participants should raise ValueError or return 0.0."
        })

    def get_provider_name(self) -> str:
        return "mock:mock-model"

    def get_execution_mode(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def list_models(self) -> List[str]:
        return ["mock-model"]

    def generate(self, prompt: str, system: Optional[str] = None, format: Optional[str] = None) -> str:
        if "repaired_content" in prompt or "TARGET FILE" in prompt:
            # Patch generation response
            return json.dumps({
                "explanation": "Added zero check for participant_count to prevent ZeroDivisionError.",
                "repaired_content": (
                    'def calculate_expense_share(total_amount: float, participant_count: int) -> float:\n'
                    '    if total_amount < 0:\n'
                    '        raise ValueError("Total amount cannot be negative")\n'
                    '    if participant_count <= 0:\n'
                    '        raise ValueError("Participant count must be greater than zero")\n'
                    '    return total_amount / participant_count\n'
                )
            })
        return self.canned_response

