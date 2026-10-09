"""Guard the initial Environment slice against peer-domain imports."""

from __future__ import annotations

import ast
from pathlib import Path


def test_runtime_modules_do_not_import_peer_domains() -> None:
    package = Path(__file__).parents[1] / "src" / "environment"
    peer_roots = {"organism", "embodiment", "world", "modality", "observation", "lab"}
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            assert not (set(names) & peer_roots), f"peer-domain import in {path}"


def test_import_namespace_matches_distribution_name() -> None:
    assert Path(__file__).parents[1].joinpath("src", "environment", "__init__.py").is_file()
