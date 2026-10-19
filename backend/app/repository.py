"""
Repository discovery, manifest inspection, file tree traversal, and safe reading.
Excludes virtual environments, .git, node_modules, build caches, and sensitive files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re

from app.security import resolve_safe_path

# Standard directories and files to exclude from indexing
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    ".idea",
    ".vscode",
}

DEFAULT_EXCLUDED_FILES = {
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}

# Supported file extensions for source viewing & search
SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".sh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
}

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB limit for safe reading


@dataclass
class FileTreeNode:
    name: str
    path: str  # relative to repo root
    is_dir: bool
    size: int = 0
    children: List["FileTreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path.replace("\\", "/"),
            "is_dir": self.is_dir,
            "size": self.size,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class RepoMetadata:
    repo_id: str
    root_path: str
    name: str
    manifest_type: Optional[str]
    has_git: bool
    test_framework: Optional[str]


def detect_repo_metadata(repo_path: str | Path, repo_id: str) -> RepoMetadata:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory does not exist: {root}")

    has_git = (root / ".git").is_dir()

    manifest_type = None
    if (root / "pyproject.toml").is_file():
        manifest_type = "pyproject.toml"
    elif (root / "setup.py").is_file():
        manifest_type = "setup.py"
    elif (root / "requirements.txt").is_file():
        manifest_type = "requirements.txt"
    elif (root / "Pipfile").is_file():
        manifest_type = "Pipfile"

    test_framework = None
    if (
        (root / "pytest.ini").is_file()
        or (root / "tests").is_dir()
        or (root / "test").is_dir()
    ):
        test_framework = "pytest"
    elif (root / "unittest").is_dir():
        test_framework = "unittest"

    return RepoMetadata(
        repo_id=repo_id,
        root_path=str(root),
        name=root.name,
        manifest_type=manifest_type,
        has_git=has_git,
        test_framework=test_framework,
    )


def get_file_tree(repo_path: str | Path, max_depth: int = 6) -> FileTreeNode:
    root = Path(repo_path).resolve()

    def build_node(current_path: Path, depth: int) -> Optional[FileTreeNode]:
        rel_path = current_path.relative_to(root).as_posix()
        if rel_path == ".":
            rel_path = ""

        if current_path.is_dir():
            if current_path.name in DEFAULT_EXCLUDED_DIRS:
                return None
            if depth > max_depth:
                return None

            children: List[FileTreeNode] = []
            try:
                entries = sorted(
                    list(current_path.iterdir()),
                    key=lambda e: (not e.is_dir(), e.name.lower()),
                )
                for entry in entries:
                    child_node = build_node(entry, depth + 1)
                    if child_node is not None:
                        children.append(child_node)
            except PermissionError:
                pass

            return FileTreeNode(
                name=current_path.name or root.name,
                path=rel_path,
                is_dir=True,
                size=0,
                children=children,
            )
        else:
            if current_path.name in DEFAULT_EXCLUDED_FILES:
                return None
            size = 0
            try:
                size = current_path.stat().st_size
            except Exception:
                pass
            return FileTreeNode(
                name=current_path.name,
                path=rel_path,
                is_dir=False,
                size=size,
            )

    root_node = build_node(root, 0)
    return (
        root_node
        if root_node
        else FileTreeNode(name=root.name, path="", is_dir=True)
    )


def read_file_safe(
    repo_path: str | Path,
    relative_file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    file_path = resolve_safe_path(repo_path, relative_file_path)

    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {relative_file_path}")

    stat = file_path.stat()
    if stat.st_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File exceeds maximum allowed size ({MAX_FILE_SIZE_BYTES} bytes)"
        )

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Could not read file {relative_file_path}: {e}")

    lines = content.splitlines()
    total_lines = len(lines)

    s = 1 if start_line is None or start_line < 1 else start_line
    e = total_lines if end_line is None or end_line > total_lines else end_line

    if s > e:
        s = e

    selected_lines = lines[s - 1 : e]
    numbered_lines = [
        {"line_number": idx, "content": text}
        for idx, text in enumerate(selected_lines, start=s)
    ]

    return {
        "file_path": relative_file_path.replace("\\", "/"),
        "total_lines": total_lines,
        "start_line": s,
        "end_line": e,
        "lines": numbered_lines,
        "raw_text": "\n".join(selected_lines),
    }


def search_repo_lexical(
    repo_path: str | Path, query: str, max_results: int = 50
) -> List[Dict[str, Any]]:
    root = Path(repo_path).resolve()
    results: List[Dict[str, Any]] = []

    if not query.strip():
        return results

    query_lower = query.lower()

    for dirpath, dirnames, filenames in os.walk(root):
        # Exclude directories in-place
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDED_DIRS]

        for filename in filenames:
            if filename in DEFAULT_EXCLUDED_FILES:
                continue

            file_ext = Path(filename).suffix.lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = Path(dirpath) / filename
            rel_path = full_path.relative_to(root).as_posix()

            try:
                if full_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue

                content = full_path.read_text(
                    encoding="utf-8", errors="replace"
                )
                lines = content.splitlines()

                for idx, line in enumerate(lines, start=1):
                    if query_lower in line.lower():
                        results.append(
                            {
                                "file_path": rel_path,
                                "line_number": idx,
                                "line_content": line.strip(),
                            }
                        )
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue

    return results
