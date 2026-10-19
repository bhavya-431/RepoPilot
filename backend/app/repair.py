"""
Bounded Repair Loop Orchestrator & Audit Trail Subsystem (Phase 5).
Coordinates bounded retry loops (maximum 2 iterations) when test failures occur,
incorporating exact pytest tracebacks and assertions back into patch generation,
and generates structured Verification Reports with full audit trails.
"""

from datetime import datetime, timezone
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm import BaseLLMProvider, OllamaProvider
from app.patcher import PatchEngine
from app.runner import TestRunner
from app.schemas import (
    GeneratePatchRequest,
    RunTestRequest,
    RepairIteration,
    RepairSessionResponse,
    VerificationReportResponse,
)

logger = logging.getLogger(__name__)


class RepairSession:
    def __init__(
        self,
        session_id: str,
        repo_id: str,
        repo_name: str,
        target_file: str,
        issue_description: str,
        root_cause: str,
        test_target: str,
        max_iterations: int = 2,
    ):
        self.session_id = session_id
        self.repo_id = repo_id
        self.repo_name = repo_name
        self.target_file = target_file
        self.issue_description = issue_description
        self.root_cause = root_cause
        self.test_target = test_target
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.status = "in_progress"  # 'in_progress', 'verified', 'max_iterations_reached', 'failed'
        self.iterations: List[RepairIteration] = []
        self.audit_events: List[Dict[str, Any]] = []
        self.final_verdict = "Repair session initialized"

    def add_audit(self, event_type: str, details: Dict[str, Any]):
        self.audit_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
        })


class RepairLoopOrchestrator:
    def __init__(
        self,
        patch_engine: PatchEngine,
        test_runner: TestRunner,
        provider: Optional[BaseLLMProvider] = None,
    ):
        self.patch_engine = patch_engine
        self.test_runner = test_runner
        self.provider = provider or OllamaProvider()
        # session_id -> RepairSession
        self.sessions: Dict[str, RepairSession] = {}

    def start_repair_session(
        self,
        repo_root: Path,
        repo_id: str,
        repo_name: str,
        target_file: str,
        issue_description: str,
        root_cause: str,
        test_target: str = "test_expense.py",
        max_iterations: int = 2,
    ) -> RepairSession:
        session_id = f"repair-{uuid.uuid4().hex[:8]}"
        session = RepairSession(
            session_id=session_id,
            repo_id=repo_id,
            repo_name=repo_name,
            target_file=target_file,
            issue_description=issue_description,
            root_cause=root_cause,
            test_target=test_target,
            max_iterations=max_iterations,
        )
        session.add_audit("session_started", {
            "target_file": target_file,
            "max_iterations": max_iterations,
            "issue": issue_description,
        })
        self.sessions[session_id] = session
        return session

    def execute_bounded_iteration(
        self,
        repo_root: Path,
        session_id: str,
        feedback: Optional[str] = None,
    ) -> RepairSessionResponse:
        """
        Executes a single bounded repair cycle:
        1. Checks max bounds (stops strictly if iteration > max_iterations).
        2. Generates patch (version v1 or v2) with feedback/traceback from previous failure.
        3. Applies patch and runs allowlisted test.
        4. Inspects outcome: if test passes, marks session 'verified'. If fails and reached max, marks 'max_iterations_reached'.
        """
        if session_id not in self.sessions:
            raise KeyError(f"Repair session not found: {session_id}")

        session = self.sessions[session_id]

        if session.current_iteration >= session.max_iterations:
            session.status = "max_iterations_reached"
            session.final_verdict = f"Terminated: Reached strict maximum boundary of {session.max_iterations} repair attempts."
            session.add_audit("max_iterations_halt", {"iteration": session.current_iteration})
            return self._session_to_response(session)

        session.current_iteration += 1
        iteration_num = session.current_iteration
        version_label = f"v{iteration_num}"

        # Combine previous failure traceback into prompt if retry
        effective_issue = session.issue_description
        if feedback:
            effective_issue += f"\nPrevious attempt feedback: {feedback}"
        elif session.iterations and session.iterations[-1].failure_traceback:
            last_tb = session.iterations[-1].failure_traceback
            effective_issue += f"\nPrevious attempt failed with traceback:\n{last_tb}"

        # 1. Synthesize patch proposal
        patch_req = GeneratePatchRequest(
            repo_id=session.repo_id,
            target_file=session.target_file,
            issue_description=effective_issue,
            suggested_fix=f"Repair iteration {version_label}",
            root_cause=session.root_cause,
        )
        proposal = self.patch_engine.generate_patch(repo_root, patch_req)
        # Label version
        proposal.version = version_label

        session.add_audit("patch_generated", {
            "version": version_label,
            "patch_id": proposal.patch_id,
            "added": proposal.diff.added_count,
            "removed": proposal.diff.removed_count,
        })

        # 2. Automatically apply patch in session for verification if applicable
        if proposal.diff.is_applicable:
            try:
                self.patch_engine.approve_and_apply_patch(repo_root, proposal.patch_id)
                session.add_audit("patch_applied", {"version": version_label, "patch_id": proposal.patch_id})
            except Exception as e:
                session.add_audit("patch_apply_warning", {"version": version_label, "error": str(e)})
        else:
            session.add_audit("patch_skipped", {"version": version_label, "reason": proposal.diff.validation_error})

        # 3. Run regression test

        test_req = RunTestRequest(
            repo_id=session.repo_id,
            test_target=session.test_target,
            timeout_seconds=20,
        )
        test_res = self.test_runner.execute_test(repo_root, test_req)

        session.add_audit("tests_executed", {
            "status": test_res.status,
            "passed": test_res.passed_count,
            "failed": test_res.failed_count,
        })

        iteration_rec = RepairIteration(
            iteration_number=iteration_num,
            patch_id=proposal.patch_id,
            version=version_label,
            patch_explanation=proposal.explanation,
            test_status=test_res.status,
            test_stdout=test_res.stdout,
            failure_traceback=test_res.failure_traceback,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.iterations.append(iteration_rec)

        if test_res.status == "passed":
            session.status = "verified"
            session.final_verdict = f"Successfully repaired and verified on attempt {version_label}."
            session.add_audit("session_verified", {"attempt": version_label})
        elif session.current_iteration >= session.max_iterations:
            session.status = "max_iterations_reached"
            session.final_verdict = f"Repair loop completed maximum {session.max_iterations} attempts without passing all tests."
            session.add_audit("session_exhausted", {"attempt": version_label})
        else:
            session.status = "in_progress"
            session.final_verdict = f"Attempt {version_label} failed. Ready for final bounded iteration."

        return self._session_to_response(session)

    def generate_verification_report(self, session_id: str) -> VerificationReportResponse:
        """
        Creates an exportable, audited Verification Report in both JSON and Markdown.
        """
        if session_id not in self.sessions:
            raise KeyError(f"Repair session not found: {session_id}")

        session = self.sessions[session_id]
        report_id = f"rep-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        is_verified = (session.status == "verified")

        # Synthesize Markdown summary
        md_lines = [
            f"# RepoPilot Verification & Audit Report",
            f"**Report ID:** `{report_id}`  ",
            f"**Repository:** `{session.repo_name}`  ",
            f"**Generated:** {timestamp}  ",
            f"**Final Status:** `{session.status.upper()}`  ",
            "",
            "## 1. Problem Diagnosis",
            f"- **Target File:** `{session.target_file}`",
            f"- **Reported Issue:** {session.issue_description}",
            f"- **Root Cause:** {session.root_cause}",
            "",
            "## 2. Bounded Repair Iterations",
            f"Total iterations executed: {len(session.iterations)} / {session.max_iterations}",
            "",
        ]

        for it in session.iterations:
            status_emoji = "✅ PASSED" if it.test_status == "passed" else "❌ FAILED"
            md_lines.append(f"### Iteration {it.version} — {status_emoji}")
            md_lines.append(f"- **Patch ID:** `{it.patch_id}`")
            md_lines.append(f"- **Explanation:** {it.patch_explanation}")
            md_lines.append(f"- **Test Status:** `{it.test_status}`")
            if it.failure_traceback:
                md_lines.append("```python")
                md_lines.append(it.failure_traceback[:500])
                md_lines.append("```")
            md_lines.append("")

        md_lines.extend([
            "## 3. Audit Trail",
            "| Timestamp | Event | Details |",
            "| :--- | :--- | :--- |",
        ])
        for event in session.audit_events:
            ts = event["timestamp"]
            ev_type = event["event_type"]
            detail_str = json.dumps(event["details"]).replace("|", "/")
            md_lines.append(f"| {ts} | `{ev_type}` | {detail_str} |")

        md_lines.extend([
            "",
            "## 4. Final Verdict",
            f"**Verdict:** {session.final_verdict}",
        ])

        markdown_report = "\n".join(md_lines)

        return VerificationReportResponse(
            report_id=report_id,
            repo_id=session.repo_id,
            repo_name=session.repo_name,
            session_id=session.session_id,
            timestamp=timestamp,
            status=session.status,
            root_cause=session.root_cause,
            fix_applied=session.iterations[-1].patch_explanation if session.iterations else "None",
            tests_verified=is_verified,
            iterations_taken=len(session.iterations),
            audit_events=session.audit_events,
            markdown_report=markdown_report,
        )

    def _session_to_response(self, session: RepairSession) -> RepairSessionResponse:
        return RepairSessionResponse(
            session_id=session.session_id,
            repo_id=session.repo_id,
            target_file=session.target_file,
            max_iterations=session.max_iterations,
            current_iteration=session.current_iteration,
            status=session.status,
            iterations=session.iterations,
            final_verdict=session.final_verdict,
        )
