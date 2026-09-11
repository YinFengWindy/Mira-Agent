"""Dependency selection for the repository-external plugin test runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import verify_plugin_tests as runner


def _plugin(
    repository: Path,
    plugin_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    optional: dict[str, tuple[str, ...]] | None = None,
) -> None:
    path = repository / "plugins" / plugin_id / "pyproject.toml"
    path.parent.mkdir(parents=True)
    text = (
        f'[project]\nname = "shiori-plugin-{plugin_id.replace("_", "-")}"\n'
        f"dependencies = {json.dumps(dependencies)}\n"
    )
    if optional:
        text += "[project.optional-dependencies]\n"
        text += "".join(
            f"{json.dumps(extra)} = {json.dumps(requirements)}\n"
            for extra, requirements in optional.items()
        )
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(runner, "REPOSITORY", tmp_path)
    _plugin(tmp_path, "default_memory")
    return tmp_path


def test_target_test_only_dependency_is_added_without_changing_runtime(
    repository: Path,
) -> None:
    _plugin(
        repository,
        "status_commands",
        dependencies=("shiori-agent==0.1.0",),
        optional={
            "test": ("shiori-plugin-testkit==0.1.0", "shiori-plugin-observe==0.1.0")
        },
    )
    _plugin(repository, "observe")

    assert runner.plugin_dependencies({"status_commands"}) == {
        "status_commands",
        "default_memory",
    }
    assert runner.plugin_dependencies(
        {"status_commands"}, extras=frozenset({"test"})
    ) == {"status_commands", "default_memory", "observe"}
    # There is deliberately no plugins/testkit directory in this repository.
    assert not (repository / "plugins/testkit").exists()


def test_sibling_runtime_chain_does_not_inherit_target_test_extra(
    repository: Path,
) -> None:
    _plugin(repository, "target", optional={"test": ("shiori-plugin-observe",)})
    _plugin(
        repository,
        "observe",
        dependencies=("shiori-plugin-citation",),
        optional={"test": ("shiori-plugin-unrequested",)},
    )
    _plugin(repository, "citation", dependencies=("shiori-plugin-target",))

    assert runner.plugin_dependencies({"target"}, extras=frozenset({"test"})) == {
        "target",
        "default_memory",
        "observe",
        "citation",
    }


def test_explicit_sibling_extra_is_processed_after_its_runtime_context(
    repository: Path,
) -> None:
    _plugin(
        repository,
        "target",
        dependencies=("shiori-plugin-observe[test]", "shiori-plugin-observe"),
    )
    _plugin(repository, "observe", optional={"test": ("shiori-plugin-audit",)})
    _plugin(repository, "audit")

    assert runner.plugin_dependencies({"target"}) == {
        "target",
        "default_memory",
        "observe",
        "audit",
    }


@pytest.mark.parametrize(
    "marker",
    ['python_version < "3"', 'sys_platform == "unavailable"', 'extra == "other"'],
)
def test_inactive_markers_do_not_require_missing_plugin_directories(
    repository: Path, marker: str
) -> None:
    _plugin(
        repository,
        "target",
        optional={"test": (f"shiori-plugin-unavailable; {marker}",)},
    )

    assert runner.plugin_dependencies({"target"}, extras=frozenset({"test"})) == {
        "target",
        "default_memory",
    }


def test_markers_use_the_active_extra_and_preserve_base_runtime_dependencies(
    repository: Path,
) -> None:
    _plugin(
        repository,
        "target",
        dependencies=(
            'shiori-plugin-runtime; extra != "test"',
            'shiori-plugin-observe; extra == "test" and python_version >= "3"',
        ),
        optional={
            "test": ("Shiori_Plugin_Testkit", "shiori-plugin-citation[render_tools]")
        },
    )
    _plugin(repository, "runtime")
    _plugin(repository, "observe")
    _plugin(
        repository,
        "citation",
        optional={"render-tools": ('shiori-plugin-audit; extra == "render_tools"',)},
    )
    _plugin(repository, "audit")

    assert runner.plugin_dependencies({"target"}, extras=frozenset({"test"})) == {
        "target",
        "default_memory",
        "runtime",
        "observe",
        "citation",
        "audit",
    }
