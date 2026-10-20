"""
Controlled Test Runner & Verification Subsystem.
Enforces allowlisted commands (pytest only), bounded timeouts, isolated working directory,
and output truncation (64KB max) to prevent denial of service or arbitrary code execution.
"""

import os
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.schemas import RunTestRequest, TestExecutionResponse
from app.security import resolve_safe_path, SecurityException

# Maximum captured stdout/stderr bytes
MAX_OUTPUT_BYTES = 64 * 1024

# Strictly allowed commands
ALLOWED_EXECUTABLES = {"pytest", "python -m pytest"}


class SecurityViolation(Exception):
    pass


class TestRunner:
    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout

    def parse_test_results(self, output: str) -> Tuple[int, int, int, Optional[str]]:
        """
        Parses pytest output to extract passed, failed, and error counts as well as failure tracebacks.
        Example summary line: '= 1 failed, 3 passed in 0.07s ='
        """
        passed = 0
        failed = 0
        errors = 0
        failure_traceback = None

        # Extract counts from summary line
        passed_m = re.search(r"(\d+)\s+passed", output)
        if passed_m:
            passed = int(passed_m.group(1))

        failed_m = re.search(r"(\d+)\s+failed", output)
        if failed_m:
            failed = int(failed_m.group(1))

        errors_m = re.search(r"(\d+)\s+error", output)
        if errors_m:
            errors = int(errors_m.group(1))

        # Extract failure tracebacks block if failures occurred
        if failed > 0 or errors > 0:
            trace_start = output.find("=== FAILURES ===")
            if trace_start == -1:
                trace_start = output.find("=== ERRORS ===")
            if trace_start != -1:
                # Capture up to summary line
                trace_end = output.find("=== short test summary info ===", trace_start)
                if trace_end != -1:
                    failure_traceback = output[trace_start:trace_end].strip()
                else:
                    failure_traceback = output[trace_start:].strip()

        return passed, failed, errors, failure_traceback

    def execute_test(self, repo_root: Path, req: RunTestRequest) -> TestExecutionResponse:
        """
        Safely executes allowlisted pytest on the target repository.
        """
        execution_id = f"test-{uuid.uuid4().hex[:8]}"
        timeout = req.timeout_seconds or self.default_timeout

        # Construct strictly controlled pytest command
        cmd = ["python", "-m", "pytest"]

        # If a specific test target is given, sanitize and validate strictly within repository boundaries
        if req.test_target:
            raw_target = req.test_target.strip().replace(";", "").replace("&", "")
            try:
                target_path = resolve_safe_path(repo_root, raw_target)
            except SecurityException:
                raise SecurityViolation("Test target path traversal detected.")

            if not target_path.exists():
                raise FileNotFoundError(f"Test target does not exist: {req.test_target}")

            rel_target = target_path.relative_to(repo_root.resolve()).as_posix()
            cmd.append(rel_target)

        # Set environment with repo_root in PYTHONPATH
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{str(repo_root)}{os.pathsep}{current_pythonpath}"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        start_time = time.time()
        cmd_str = " ".join(cmd)

        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(repo_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                stdout_data, stderr_data = process.communicate(timeout=timeout)
                duration = round(time.time() - start_time, 2)
                exit_code = process.returncode

                # Truncate if exceeds MAX_OUTPUT_BYTES
                if len(stdout_data.encode("utf-8")) > MAX_OUTPUT_BYTES:
                    stdout_data = stdout_data[:MAX_OUTPUT_BYTES] + "\n... [TRUNCATED - EXCEEDED 64KB LIMIT]"
                if len(stderr_data.encode("utf-8")) > MAX_OUTPUT_BYTES:
                    stderr_data = stderr_data[:MAX_OUTPUT_BYTES] + "\n... [TRUNCATED - EXCEEDED 64KB LIMIT]"

                passed, failed, errors, failure_tb = self.parse_test_results(stdout_data + "\n" + stderr_data)

                if exit_code == 0:
                    status = "passed"
                elif failed > 0 or errors > 0:
                    status = "failed"
                else:
                    status = "error"

                return TestExecutionResponse(
                    execution_id=execution_id,
                    repo_id=req.repo_id,
                    command=cmd_str,
                    status=status,
                    exit_code=exit_code,
                    passed_count=passed,
                    failed_count=failed,
                    error_count=errors,
                    duration_seconds=duration,
                    stdout=stdout_data,
                    stderr=stderr_data,
                    failure_traceback=failure_tb,
                )

            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                duration = round(time.time() - start_time, 2)
                return TestExecutionResponse(
                    execution_id=execution_id,
                    repo_id=req.repo_id,
                    command=cmd_str,
                    status="timeout",
                    exit_code=-1,
                    passed_count=0,
                    failed_count=0,
                    error_count=1,
                    duration_seconds=duration,
                    stdout="",
                    stderr=f"Test execution exceeded maximum timeout of {timeout}s.",
                    failure_traceback=f"TimeoutExpired: Test run killed after {timeout} seconds.",
                )

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return TestExecutionResponse(
                execution_id=execution_id,
                repo_id=req.repo_id,
                command=cmd_str,
                status="error",
                exit_code=-1,
                passed_count=0,
                failed_count=0,
                error_count=1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                failure_traceback=str(e),
            )
