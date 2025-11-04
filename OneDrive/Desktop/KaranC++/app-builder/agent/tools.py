import pathlib
import subprocess
from typing import Tuple

from langchain_core.tools import tool

PROJECT_ROOT = pathlib.Path.cwd() / "generated_project"


def safe_path_for_project(path: str) -> pathlib.Path:
    p = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT.resolve() not in p.parents and PROJECT_ROOT.resolve() != p.parent and PROJECT_ROOT.resolve() != p:
        raise ValueError("Attempt to write outside project root")
    return p


# Helper function to actually write a file
def _write_file_impl(path: str, content: str) -> str:
    p = safe_path_for_project(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return f"WROTE:{p}"


@tool("repo_browser.write_file")
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    return _write_file_impl(path, content)


@tool("write_file")
def write_file_no_prefix(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    return _write_file_impl(path, content)


# Helper function to read
def _read_file_impl(path: str) -> str:
    p = safe_path_for_project(path)
    if not p.exists():
        return ""
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


@tool("repo_browser.read_file")
def read_file(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    return _read_file_impl(path)


@tool("read_file")
def read_file_no_prefix(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    return _read_file_impl(path)


@tool("repo_browser.get_current_directory")
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(PROJECT_ROOT)


@tool("get_current_directory")
def get_current_directory_no_prefix() -> str:
    """Returns the current working directory."""
    return str(PROJECT_ROOT)


# Helper for list_file
def _list_file_impl(directory: str = ".") -> str:
    p = safe_path_for_project(directory)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(PROJECT_ROOT)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."


@tool("repo_browser.list_file")
def list_file(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    return _list_file_impl(directory)


@tool("list_file")
def list_file_no_prefix(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    return _list_file_impl(directory)


# Helper for print_tree
def _print_tree_impl(path: str = ".", depth: int = 3) -> str:
    p = safe_path_for_project(path)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"

    def build_tree(directory, prefix="", current_depth=0):
        if current_depth >= depth:
            return []

        contents = []
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                contents.append(f"{prefix}{current_prefix}{item.name}")

                if item.is_dir() and current_depth < depth - 1:
                    extension = "    " if is_last else "│   "
                    contents.extend(build_tree(item, prefix + extension, current_depth + 1))
        except PermissionError:
            pass

        return contents

    tree_lines = [str(p.relative_to(PROJECT_ROOT.parent)) + "/"]
    tree_lines.extend(build_tree(p))
    return "\n".join(tree_lines)


@tool("repo_browser.print_tree")
def print_tree(path: str = ".", depth: int = 3) -> str:
    """Prints a tree structure of files and directories up to a certain depth."""
    return _print_tree_impl(path, depth)


@tool("print_tree")
def print_tree_no_prefix(path: str = ".", depth: int = 3) -> str:
    """Prints a tree structure of files and directories up to a certain depth."""
    return _print_tree_impl(path, depth)


# Helper for open_file
def _open_file_impl(path: str, line_start: int = 1, line_end: int = None) -> str:
    p = safe_path_for_project(path)
    if not p.exists():
        return f"ERROR: File {path} does not exist"

    try:
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_idx = max(0, line_start - 1)
        end_idx = len(lines) if line_end is None else min(len(lines), line_end)

        selected_lines = lines[start_idx:end_idx]
        return "".join(selected_lines)
    except Exception as e:
        return f"ERROR: Could not read file {path}: {str(e)}"


@tool("repo_browser.open_file")
def open_file(path: str, line_start: int = 1, line_end: int = None) -> str:
    """Opens a file and returns specific lines. If line_end is None, returns from line_start to end."""
    return _open_file_impl(path, line_start, line_end)


@tool("open_file")
def open_file_no_prefix(path: str, line_start: int = 1, line_end: int = None) -> str:
    """Opens a file and returns specific lines. If line_end is None, returns from line_start to end."""
    return _open_file_impl(path, line_start, line_end)


@tool
def run_cmd(cmd: str, cwd: str = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result."""
    cwd_dir = safe_path_for_project(cwd) if cwd else PROJECT_ROOT
    res = subprocess.run(cmd, shell=True, cwd=str(cwd_dir), capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr


def init_project_root():
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    return str(PROJECT_ROOT)