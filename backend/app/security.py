import os
import re
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Optional


class SecurityException(Exception):
    pass


def resolve_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """
    Resolves target_path relative to base_dir, ensuring that the resolved path
    is strictly contained within base_dir.
    Guarantees cross-platform defense against Windows drive paths (C:), UNC shares (\\\\),
    forward/backward slash traversal attempts, and absolute paths escaping the root.
    Raises SecurityException if path traversal is detected.
    """
    base = Path(base_dir).resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"Base repository directory does not exist: {base}")

    raw_target_str = str(target_path).strip()

    # 1. Proactively detect traversal patterns across platforms
    # Check for raw .. segments in both slash formats
    normalized_separators = raw_target_str.replace("\\", "/")
    segments = [seg for seg in normalized_separators.split("/") if seg]

    # Explicitly disallow Windows drive letters or root paths on POSIX/Windows if they escape base
    is_win_abs = bool(re.match(r"^[a-zA-Z]:", raw_target_str))
    is_unc = raw_target_str.startswith(r"\\") or raw_target_str.startswith("//")

    target = Path(raw_target_str)

    if is_unc:
        raise SecurityException(
            f"Path traversal detected: UNC path '{raw_target_str}' is outside repository root '{base}'"
        )

    if is_win_abs or target.is_absolute():
        # Absolute path provided
        try:
            resolved = Path(raw_target_str).resolve()
        except Exception:
            raise SecurityException(f"Invalid path traversal syntax: '{raw_target_str}'")
    else:
        # Relative path provided
        resolved = (base / target).resolve()

    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityException(
            f"Path traversal detected: '{target_path}' resolves outside repository root '{base}'"
        )

    return resolved
