"""plugin.config.get/set：schema 通道读写，覆盖验收标准 3 与 4。

用真实的 legacy 插件（仓库自带的 qqbot，经 ``Plugin.ConfigModel`` 声明配置
模型）和一个完全没有配置模型的旧插件（hello 夹具）做被测对象，而不是只能
造假插件；证明 ``plugin.config`` 通道对存量插件立刻可用。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent.config import load_config_text
from bootstrap.app import AppRuntime, RuntimeFeatures
from core.roles.store import RoleStore
from desktop_bridge.runtime.service import ReloadableDesktopService

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_QQBOT_PLUGIN_DIR = _REPOSITORY_ROOT / "apps" / "backend" / "plugins" / "qqbot"
_HELLO_FIXTURE_DIR = _REPOSITORY_ROOT / "tests" / "fixtures" / "plugins" / "hello"
_NULLABLE_FIXTURE_DIR = (
    _REPOSITORY_ROOT / "tests" / "fixtures" / "plugins" / "nullable_config"
)


def _config() -> str:
    return (
        "[llm]\nregistrations = []\n"
        "\n[agent.maintenance]\nmemory_optimizer_enabled = false\n"
        '\n[proactive]\nenabled = false\nprofile = "quiet"\n'
    )


def _stage_plugin_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stages qqbot (has ConfigModel), hello (has none) and a nullable-default model."""
    root = tmp_path / "plugin_dirs"
    shutil.copytree(_QQBOT_PLUGIN_DIR, root / "qqbot")
    shutil.copytree(_HELLO_FIXTURE_DIR, root / "hello")
    shutil.copytree(_NULLABLE_FIXTURE_DIR, root / "nullable_config")
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda workspace: [root])


async def _start_service(tmp_path: Path) -> tuple[ReloadableDesktopService, Path, AppRuntime]:
    path = tmp_path / "config.toml"
    path.write_text(_config(), encoding="utf-8")
    app = AppRuntime(
        load_config_text(_config()), tmp_path,
        features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False),
    )
    await app.start()
    service = ReloadableDesktopService(app, path, RoleStore(tmp_path))
    return service, path, app


async def _request(service: ReloadableDesktopService, method: str, payload=None):
    return await service.handle(
        {"id": method, "method": method, "payload": payload or {}},
        emit_event=lambda event: None,
    )


@pytest.mark.asyncio
async def test_get_returns_schema_and_default_backed_values(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, _, app = await _start_service(tmp_path)
    try:
        response = await _request(service, "plugin.config.get", {"plugin_id": "qqbot"})

        assert response.error is None, response.error
        assert response.payload["plugin_id"] == "qqbot"
        assert response.payload["schema"]["title"] == "QQBotConfigModel"
        # 未写入过配置：值来自模型默认值补全
        assert response.payload["values"]["app_id"] == ""
        assert response.payload["values"]["client_secret"] == ""
        assert response.payload["values"]["allow_from"] == []
    finally:
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_get_reports_null_schema_for_a_plugin_without_a_config_model(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, _, app = await _start_service(tmp_path)
    try:
        response = await _request(service, "plugin.config.get", {"plugin_id": "hello"})

        assert response.error is None, response.error
        assert response.payload["schema"] is None
        assert response.payload["values"] == {}
    finally:
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_set_rejects_a_plugin_without_a_config_model_and_writes_nothing(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        before = path.read_text(encoding="utf-8")

        response = await _request(service, "plugin.config.set", {
            "plugin_id": "hello", "operation_id": "op-unsupported", "values": {"anything": 1},
        })

        assert response.error is not None
        assert response.error.code == "plugin_config_unsupported"
        assert path.read_text(encoding="utf-8") == before
    finally:
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_set_rejects_invalid_values_and_writes_nothing(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        before = path.read_text(encoding="utf-8")

        response = await _request(service, "plugin.config.set", {
            "plugin_id": "qqbot", "operation_id": "op-invalid",
            "values": {"allow_from": 123},
        })

        assert response.error is not None
        assert response.error.code == "plugin_config_invalid"
        # 校验失败必须原样保留磁盘文件，一个字节都不能改
        assert path.read_text(encoding="utf-8") == before
    finally:
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_set_validates_commits_and_survives_a_restart(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        response = await _request(service, "plugin.config.set", {
            "plugin_id": "qqbot", "operation_id": "op-valid",
            "values": {"app_id": "app-123", "client_secret": "secret-xyz"},
        })

        assert response.error is None, response.error
        assert response.payload["plugin_id"] == "qqbot"
        assert response.payload["values"]["app_id"] == "app-123"
        assert response.payload["values"]["client_secret"] == "secret-xyz"
        assert "generation" in response.payload

        # 落盘确认：磁盘文件已包含新值
        on_disk = path.read_text(encoding="utf-8")
        assert "app-123" in on_disk
        assert "secret-xyz" in on_disk

        # 同一 generation 内立即读回一致
        after = await _request(service, "plugin.config.get", {"plugin_id": "qqbot"})
        assert after.payload["values"]["app_id"] == "app-123"
    finally:
        await service.aclose()
        await app.shutdown()

    # 模拟进程重启：脱离当前运行时，从磁盘文件重新解析配置
    restarted = load_config_text(path.read_text(encoding="utf-8"))
    assert restarted.plugins["qqbot"]["app_id"] == "app-123"
    assert restarted.plugins["qqbot"]["client_secret"] == "secret-xyz"


@pytest.mark.asyncio
async def test_set_refuses_a_value_toml_cannot_represent(tmp_path, monkeypatch):
    """校验通过但落盘会失真的值必须被拒绝，而不是静默写成默认值。

    TOML 没有 null，``toml.dumps`` 会直接丢弃 None 字段。对一个"可空但默认值
    非空"的字段写 null，如果照常提交，重启后读回的是默认值而不是用户存的 null，
    用户的写入被静默改写。这里断言这种情况被识别并整体拒绝。
    """
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        before = path.read_text(encoding="utf-8")

        response = await _request(service, "plugin.config.set", {
            "plugin_id": "nullable_config", "operation_id": "op-null",
            "values": {"label": None},
        })

        assert response.error is not None
        assert response.error.code == "plugin_config_unrepresentable"
        assert path.read_text(encoding="utf-8") == before
    finally:
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_set_requires_plugin_id_and_operation_id(tmp_path, monkeypatch):
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        before = path.read_text(encoding="utf-8")

        missing_plugin_id = await _request(service, "plugin.config.set", {
            "operation_id": "op-1", "values": {},
        })
        missing_operation_id = await _request(service, "plugin.config.set", {
            "plugin_id": "qqbot", "values": {},
        })

        assert missing_plugin_id.error.code == "runtime_invalid_request"
        assert missing_operation_id.error.code == "runtime_invalid_request"
        assert path.read_text(encoding="utf-8") == before
    finally:
        await service.aclose()
        await app.shutdown()
