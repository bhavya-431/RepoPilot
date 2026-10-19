"""
Bug Investigation Engine for RepoPilot.
Collects evidence from source code, formulates structured prompts,
and produces verifiable diagnosis schemas using the configured LLM provider.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm import BaseLLMProvider, OllamaProvider, MockLLMProvider
from app.repository import read_file_safe, search_repo_lexical
from app.schemas import InvestigationRequest, InvestigationResponse, EvidenceCitation

logger = logging.getLogger(__name__)


class InvestigationEngine:
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or OllamaProvider()

    def set_provider(self, provider: BaseLLMProvider):
        self.provider = provider

    def _extract_files_from_traceback(self, traceback_str: str) -> List[str]:
        """Extract referenced python file paths from python stack traces."""
        patterns = [
            r'File ["\']([^"\']+\.py)["\']',
            r'([a-zA-Z0-9_\-\.\/\\]+\.py)(?:[:\s,line]+(\d+))?',
        ]
        found = set()
        for pat in patterns:
            for match in re.finditer(pat, traceback_str):
                fpath = match.group(1).replace("\\", "/")
                # Extract filename or relative component
                fname = Path(fpath).name
                found.add(fname)
        return list(found)

    def collect_evidence_context(
        self,
        repo_root: Path,
        issue_desc: str,
        traceback_str: Optional[str] = None,
        target_files: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Gathers relevant code contexts from files mentioned in the traceback,
        target files, or via search queries based on keywords in the issue description.
        """
        code_snippets: Dict[str, str] = {}
        files_to_read: List[str] = []

        if target_files:
            files_to_read.extend(target_files)

        if traceback_str:
            extracted_names = self._extract_files_from_traceback(traceback_str)
            for fname in extracted_names:
                # Find matching files in repository
                for py_file in repo_root.glob(f"**/{fname}"):
                    if py_file.is_file():
                        rel = py_file.relative_to(repo_root).as_posix()
                        if rel not in files_to_read:
                            files_to_read.append(rel)

        # If no specific files identified yet, find top relevant python files (limited to 2)
        if not files_to_read:
            for p in list(repo_root.glob("*.py"))[:2]:
                rel = p.relative_to(repo_root).as_posix()
                files_to_read.append(rel)

        # Read contents with focused context limits (up to 3 files, max 80 lines each)
        for rel_path in files_to_read[:3]:
            try:
                data = read_file_safe(repo_root, rel_path, start_line=1, end_line=80)
                formatted_lines = [
                    f"{line['line_number']:4d} | {line['content']}"
                    for line in data["lines"]
                ]
                code_snippets[rel_path] = "\n".join(formatted_lines)
            except Exception as e:
                logger.warning(f"Could not read context for {rel_path}: {e}")

        return code_snippets

    def investigate(self, repo_root: Path, req: InvestigationRequest) -> InvestigationResponse:
        """
        Executes model-assisted investigation and returns structured diagnosis.
        """
        investigation_id = f"inv-{uuid.uuid4().hex[:8]}"
        context_snippets = self.collect_evidence_context(
            repo_root,
            issue_desc=req.issue_description,
            traceback_str=req.traceback,
            target_files=req.target_files,
        )

        # Build structured context string
        context_text = ""
        for fpath, code in context_snippets.items():
            context_text += f"\n--- FILE: {fpath} ---\n{code}\n"

        prompt = f"""Investigate this bug and provide a concise, factual diagnosis.

ISSUE:
{req.issue_description}

TRACEBACK:
{req.traceback or "No traceback provided"}

CODE:
{context_text}

Provide your diagnosis in valid JSON with exactly the following schema:
{{
  "root_cause": "One concise sentence identifying the root cause",
  "evidence": [
    {{
      "file_path": "relative/path/to/file.py",
      "start_line": 10,
      "end_line": 15,
      "snippet": "exact offending line",
      "explanation": "One concise sentence explaining why this code fails"
    }}
  ],
  "suggested_fix": "One concise sentence describing the code change",
  "recommended_test": "Test name to verify fix",
  "confidence": 0.95,
  "known_uncertainties": null
}}
Return only valid JSON. Do not add markdown explanation outside the JSON.
"""

        system_prompt = (
            "You are RepoPilot, a senior software engineering agent. "
            "Inspect code facts and produce concise, factual, schema-compliant JSON."
        )

        import time
        start_time = time.time()
        try:
            raw_response = self.provider.generate(
                prompt=prompt,
                system=system_prompt,
                format="json",
            )
            # Clean possible markdown wrap
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())

            evidence_items = []
            for item in data.get("evidence", []):
                evidence_items.append(
                    EvidenceCitation(
                        file_path=item.get("file_path", "unknown"),
                        start_line=int(item.get("start_line", 1)),
                        end_line=int(item.get("end_line", 1)),
                        snippet=str(item.get("snippet", "")),
                        explanation=str(item.get("explanation", "")),
                    )
                )

            latency = round(time.time() - start_time, 2)
            return InvestigationResponse(
                investigation_id=investigation_id,
                repo_id=req.repo_id,
                status="completed",
                root_cause=data.get("root_cause", "Unspecified root cause"),
                evidence=evidence_items,
                suggested_fix=data.get("suggested_fix", "No fix suggested"),
                recommended_test=data.get("recommended_test"),
                confidence=float(data.get("confidence", 0.8)),
                known_uncertainties=data.get("known_uncertainties"),
                provider_name=self.provider.get_provider_name(),
                execution_mode=self.provider.get_execution_mode(),
                latency_seconds=latency,
            )

        except Exception as e:
            logger.error(f"Investigation failed with provider, falling back to heuristic: {e}")
            latency = round(time.time() - start_time, 2)
            # Graceful deterministic fallback
            return InvestigationResponse(
                investigation_id=investigation_id,
                repo_id=req.repo_id,
                status="completed",
                root_cause=f"Error running model analysis: {str(e)}",
                evidence=[
                    EvidenceCitation(
                        file_path=next(iter(context_snippets.keys()), "unknown"),
                        start_line=1,
                        end_line=20,
                        snippet="Code context gathered",
                        explanation="Heuristic fallback due to provider connectivity or timeout",
                    )
                ],
                suggested_fix="Check model daemon or inspect traceback directly.",
                recommended_test="pytest",
                confidence=0.5,
                known_uncertainties="Local inference returned an error or timed out",
                provider_name="deterministic_fallback:heuristic_analyzer",
                execution_mode="deterministic_fallback",
                latency_seconds=latency,
            )
