from __future__ import annotations

import json
from pathlib import Path


def test_repository_entrypoints_are_desktop_first():
    repo_root = Path(__file__).resolve().parents[2]
    package_json = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    scripts = package_json["scripts"]

    assert scripts["start"] == "pnpm run desktop:start"
    assert scripts["dev"] == "pnpm run desktop:dev"
    assert "dashboard:dev" not in scripts
    assert "dashboard:build" not in scripts
    assert "build:dashboard" not in scripts
    assert "build:dashboard:watch" not in scripts

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "npm run dashboard:dev" not in readme
    assert "npm run dashboard:build" not in readme
    assert "main.py dashboard" not in readme
