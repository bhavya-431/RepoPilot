"""
Safe path resolution and workspace boundary validation.
Ensures no directory traversal or access outside authorized boundaries.
"""

from pathlib import Path
from typing import Optional


class SecurityException(Exception):
    pass


def resolve_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """
    Resolves target_path relative to base_dir, ensuring that the resolved path
    is strictly contained within base_dir.
    Raises SecurityException if path traversal is detected.
    """
    base = Path(base_dir).resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"Base repository directory does not exist: {base}")

    # Prevent absolute paths or leading slashes from jumping out of base
    target = Path(target_path)
    if target.is_absolute():
        resolved = target.resolve()
    else:
        resolved = (base / target).resolve()

    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityException(
            f"Path traversal detected: '{target_path}' resolves outside repository root '{base}'"
        )

    return resolved
