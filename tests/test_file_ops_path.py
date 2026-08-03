"""Path isolation tests for file_ops."""

from pathlib import Path

from src.tools.file_ops import _safe_path, _workspace_root


def test_safe_path_allows_inside():
    p = _safe_path(".")
    assert p == _workspace_root()


def test_safe_path_blocks_escape():
    # relative_to rejects paths outside workspace
    outside = str(Path(_workspace_root()).anchor)  # e.g. "/" or "C:\\"
    try:
        _safe_path(outside)
        # On some systems joining "/" may still resolve under root differently;
        # force with parent traversal
        _safe_path("../" * 20 + "etc/passwd")
        assert False, "expected PermissionError"
    except PermissionError:
        pass
