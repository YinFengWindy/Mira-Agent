"""plugin.config.get/set：schema 通道读写，覆盖验收标准 3 与 4。

用真实的 legacy 插件（仓库自带的 qqbot，经 ``Plugin.ConfigModel`` 声明配置
模型）和一个完全没有配置模型的旧插件（hello 夹具）做被测对象，而不是只能
造假插件；证明 ``plugin.config`` 通道对存量插件立刻可用。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agent.config import load_config_text
from bootstrap.app import AppRuntime, RuntimeFeatures
from conftest import stage_plugin_fixture
from core.roles.store import RoleStore
from desktop_bridge.runtime.service import ReloadableDesktopService

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_QQBOT_PLUGIN_DIR = _REPOSITORY_ROOT / "plugins" / "qqbot"
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
    # 夹具是旧扁平布局，内核要求 backend/；不重整的话这些插件根本不会被加载，
    # 而「无配置模型返回 schema=None」这类断言在插件缺席时也成立，测试会假绿。
    _ = stage_plugin_fixture("hello", root)
    _ = stage_plugin_fixture("nullable_config", root)
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
        # 插件缺席时上面两条也成立，必须确认它真的被加载了，否则是假绿
        kernel = app.core.plugin_manager
        assert kernel is not None
        assert any(item["id"] == "hello" for item in kernel.states())
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

    # 只证明磁盘文件正确还不够：验收标准要求"写入成功后事务化应用并在重启后
    # 保持"，真正需要证明的是重启后的运行时能读回新值，而不只是磁盘字节正确。
    # 用同一份配置文件重新构建一个全新的 AppRuntime + ReloadableDesktopService，
    # 模拟进程重启后重新启动桥接。
    restarted_app = AppRuntime(
        restarted, tmp_path,
        features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False),
    )
    await restarted_app.start()
    restarted_service = ReloadableDesktopService(restarted_app, path, RoleStore(tmp_path))
    try:
        response_after_restart = await _request(
            restarted_service, "plugin.config.get", {"plugin_id": "qqbot"},
        )
        assert response_after_restart.error is None, response_after_restart.error
        assert response_after_restart.payload["values"]["app_id"] == "app-123"
        assert response_after_restart.payload["values"]["client_secret"] == "secret-xyz"
    finally:
        await restarted_service.aclose()
        await restarted_app.shutdown()


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
async def test_set_rejects_a_merge_that_corrupts_an_unrelated_table(tmp_path, monkeypatch):
    """整份文档回读守卫：目标表之外的任何键值变化都必须整体拒绝。

    之前的守卫只重新校验目标插件自己的那张表，对合并逻辑意外改动了别的表
    （例如行扫描定位表头出错）视而不见——目标表校验照常通过，写入照常提交，
    用户配置被静默破坏。这里模拟一次"合并结果本身仍能通过目标表校验，但
    顺带改动了无关表"的合并，断言它现在会被整体拒绝而不是被放行。
    """
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, path, app = await _start_service(tmp_path)
    try:
        before = path.read_text(encoding="utf-8")

        import desktop_bridge.runtime.plugin_config as plugin_config_module
        from desktop_bridge.plugin_config_text import merge_plugin_table as real_merge

        def _merge_but_corrupt_an_unrelated_table(config_toml, plugin_id, values):
            merged = real_merge(config_toml, plugin_id, values)
            assert 'profile = "quiet"' in merged
            return merged.replace('profile = "quiet"', 'profile = "loud"')

        monkeypatch.setattr(
            plugin_config_module, "merge_plugin_table", _merge_but_corrupt_an_unrelated_table,
        )

        response = await _request(service, "plugin.config.set", {
            "plugin_id": "qqbot", "operation_id": "op-corrupt",
            "values": {"app_id": "app-1", "client_secret": "secret-1"},
        })

        assert response.error is not None
        assert response.error.code == "plugin_config_unrepresentable"
        # 目标表校验本身会通过（app_id/client_secret 都合法），必须靠整份文档
        # 对比才能发现 [proactive] 被意外改动，写入必须整体取消。
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


@pytest.mark.asyncio
async def test_get_returns_json_safe_defaults(tmp_path, monkeypatch):
    """默认值必须以 JSON 形态返回，否则 plugin.config.get 会在传输层炸掉。

    ``defaults_for`` 直接从 ``model_fields`` 取默认值，拿到的是原始 Python 对象；
    而这个结果会与已存值合并后经桥接序列化回 renderer。模型里一旦有 Enum /
    datetime / Path / 嵌套模型这类默认值，原样送上传输层就会失败。
    """
    _stage_plugin_dirs(tmp_path, monkeypatch)
    service, _, app = await _start_service(tmp_path)
    try:
        response = await _request(
            service, "plugin.config.get", {"plugin_id": "nullable_config"},
        )

        assert response.error is None, response.error
        # Enum 默认值必须已经是它的 JSON 值，而不是 Enum 实例
        assert response.payload["values"]["mode"] == "quiet"
        # 最直接的证据：整个响应能被 JSON 序列化
        _ = json.dumps(response.payload)
    finally:
        await service.aclose()
        await app.shutdown()
