from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import main as app_main


def test_main_help_prints_usage(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc_info:
        app_main.main(["--help"])

    assert exc_info.value.code == 0
    assert "bridge" in capsys.readouterr().out


def test_main_accepts_desktop_as_bridge_alias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    serve_bridge = AsyncMock()
    monkeypatch.setattr(app_main, "serve_bridge", serve_bridge)

    exit_code = app_main.main(["desktop", "--config", str(config_path)])

    assert exit_code == 0
    serve_bridge.assert_awaited_once_with(str(config_path), None)


@pytest.mark.asyncio
async def test_inspect_modules_prints_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    class _Runtime:
        memory_runtime = SimpleNamespace(aclose=AsyncMock())

        async def inspect_modules(self):
            return {"memory": "ready"}

        async def stop(self):
            return None

    class _HttpResources:
        async def aclose(self):
            return None

    monkeypatch.setattr(app_main.Config, "load", lambda _: object())
    monkeypatch.setattr(app_main, "SharedHttpResources", _HttpResources)
    monkeypatch.setattr(
        "bootstrap.tools.build_core_runtime",
        lambda config, workspace, http_resources: _Runtime(),
    )

    await app_main.inspect_modules(workspace=tmp_path)

    assert "{'memory': 'ready'}" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_module_inspection_closes_http_when_construction_fails(monkeypatch, tmp_path):
    http = SimpleNamespace(aclose=AsyncMock())
    monkeypatch.setattr(app_main.Config, "load", lambda _: object())
    monkeypatch.setattr(app_main, "SharedHttpResources", lambda: http)

    def fail(*args):
        raise ValueError("invalid wiring")

    monkeypatch.setattr("bootstrap.tools.build_core_runtime", fail)
    with pytest.raises(ValueError, match="invalid wiring"):
        await app_main.inspect_modules(workspace=tmp_path)
    http.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_module_entrypoint_exit_codes(monkeypatch: pytest.MonkeyPatch):
    """以 `python -m main` 方式运行时的三条退出路径。"""
    import runpy
    import sys

    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
    monkeypatch.setattr(sys, "argv", ["main.py", "--config", "missing.json"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("main", run_name="__main__")
    assert exc.value.code == 1

    def _fake_asyncio_run(coro):
        coro.close()
        return None

    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr("asyncio.run", _fake_asyncio_run)
    monkeypatch.setattr(
        "agent.config.Config.load",
        classmethod(lambda cls, path="config.toml": SimpleNamespace()),
    )
    monkeypatch.setattr(
        "bootstrap.app.build_app_runtime",
        lambda *args, **kwargs: SimpleNamespace(run=AsyncMock()),
    )
    monkeypatch.setattr(sys, "argv", ["main.py", "cli"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("main", run_name="__main__")
    assert exc.value.code == 2

    monkeypatch.setattr(sys, "argv", ["main.py"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("main", run_name="__main__")
    assert exc.value.code == 0
