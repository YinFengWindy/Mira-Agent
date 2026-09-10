"""Shared fixtures and test bootstrap helpers."""

import asyncio
import inspect
import os
import shutil
import sys
import types
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = REPO_ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))
os.environ.setdefault("PYTHONPATH", str(VENV_SITE_PACKAGES))

# Provide a lightweight openai stub in test env so imports do not fail
# when optional runtime dependency is absent.
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _DummyChatCompletions:
        async def create(self, *args, **kwargs):
            raise RuntimeError(
                "openai stub: AsyncOpenAI.chat.completions.create not mocked"
            )

    class _DummyChat:
        def __init__(self):
            self.completions = _DummyChatCompletions()

    class AsyncOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = _DummyChat()
            self.closed = False

        async def close(self):
            self.closed = True

    openai_stub.AsyncOpenAI = AsyncOpenAI
    sys.modules["openai"] = openai_stub

# Provide lightweight telegram stubs so optional messaging deps do not block
# unrelated test collection.
if "telegram" not in sys.modules:
    telegram_stub = types.ModuleType("telegram")
    telegram_error_stub = types.ModuleType("telegram.error")

    class Bot:
        async def edit_message_text(self, *args, **kwargs):
            return True

    class TelegramMessageEntity:
        def __init__(self, *, type, offset, length):
            self.type = type
            self.offset = offset
            self.length = length

    class RetryAfter(Exception):
        def __init__(self, retry_after=1.0):
            super().__init__(f"retry after {retry_after}")
            self.retry_after = retry_after

    class NetworkError(Exception):
        pass

    class BadRequest(Exception):
        pass

    class TimedOut(Exception):
        pass

    telegram_stub.Bot = Bot
    telegram_stub.MessageEntity = TelegramMessageEntity
    telegram_error_stub.BadRequest = BadRequest
    telegram_error_stub.RetryAfter = RetryAfter
    telegram_error_stub.NetworkError = NetworkError
    telegram_error_stub.TimedOut = TimedOut
    sys.modules["telegram"] = telegram_stub
    sys.modules["telegram.error"] = telegram_error_stub

if "telegramify_markdown.converter" not in sys.modules:
    telegramify_stub = types.ModuleType("telegramify_markdown")
    converter_stub = types.ModuleType("telegramify_markdown.converter")
    entity_stub = types.ModuleType("telegramify_markdown.entity")

    class MessageEntity:
        def __init__(
            self,
            *,
            type,
            offset,
            length,
            url=None,
            language=None,
            custom_emoji_id=None,
        ):
            self.type = type
            self.offset = offset
            self.length = length
            self.url = url
            self.language = language
            self.custom_emoji_id = custom_emoji_id

        def to_dict(self):
            data = {
                "type": self.type,
                "offset": self.offset,
                "length": self.length,
            }
            if self.url is not None:
                data["url"] = self.url
            if self.language is not None:
                data["language"] = self.language
            if self.custom_emoji_id is not None:
                data["custom_emoji_id"] = self.custom_emoji_id
            return data

    def convert_with_segments(text):
        if text.startswith("```") and text.endswith("```"):
            first_newline = text.find("\n")
            code = text[first_newline + 1 : -3] if first_newline != -1 else ""
            entity = MessageEntity(type="pre", offset=0, length=len(code))
            return code, [entity], []
        return text, [], []

    def split_entities(text, entities, limit):
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + limit, len(text))
            chunk_text = text[start:end]
            chunk_entities = []
            for entity in entities:
                entity_start = entity.offset
                entity_end = entity.offset + entity.length
                overlap_start = max(start, entity_start)
                overlap_end = min(end, entity_end)
                if overlap_end <= overlap_start:
                    continue
                chunk_entities.append(
                    MessageEntity(
                        type=entity.type,
                        offset=overlap_start - start,
                        length=overlap_end - overlap_start,
                        url=entity.url,
                        language=entity.language,
                        custom_emoji_id=entity.custom_emoji_id,
                    )
                )
            chunks.append((chunk_text, chunk_entities))
            start = end
        return chunks or [("", [])]

    converter_stub.convert_with_segments = convert_with_segments
    entity_stub.MessageEntity = MessageEntity
    entity_stub.split_entities = split_entities
    sys.modules["telegramify_markdown"] = telegramify_stub
    sys.modules["telegramify_markdown.converter"] = converter_stub
    sys.modules["telegramify_markdown.entity"] = entity_stub

if "json_repair" not in sys.modules:
    json_repair_stub = types.ModuleType("json_repair")

    def loads(text, *args, **kwargs):
        import json

        return json.loads(text)

    def repair_json(text, *args, **kwargs):
        return text

    json_repair_stub.loads = loads
    json_repair_stub.repair_json = repair_json
    sys.modules["json_repair"] = json_repair_stub

if "uvicorn" not in sys.modules:
    uvicorn_stub = types.ModuleType("uvicorn")

    def run(*args, **kwargs):
        raise RuntimeError("uvicorn stub: run() not expected in tests")

    uvicorn_stub.run = run
    sys.modules["uvicorn"] = uvicorn_stub

from agent.scheduler import LatencyTracker, SchedulerService, ScheduledJob


def make_job(
    trigger="at",
    tier="instant",
    fire_at=None,
    channel="telegram",
    chat_id="123",
    message: str | None = "hello",
    prompt=None,
    name=None,
    interval_seconds=None,
    cron_expr=None,
    timezone_="UTC",
    role_id="mira",
) -> ScheduledJob:
    if fire_at is None:
        fire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    return ScheduledJob(
        trigger=trigger,
        tier=tier,
        fire_at=fire_at,
        channel=channel,
        chat_id=chat_id,
        role_id=role_id,
        message=message,
        prompt=prompt,
        name=name,
        interval_seconds=interval_seconds,
        cron_expr=cron_expr,
        timezone=timezone_,
    )


@pytest.fixture
def mock_push():
    m = AsyncMock()
    m.execute = AsyncMock(return_value="文本已发送")
    return m


@pytest.fixture
def mock_loop():
    m = AsyncMock()
    m.process_direct = AsyncMock(return_value="AI response")

    async def _run_role_operation(_metadata, operation):
        return await operation()

    m.run_role_operation = AsyncMock(side_effect=_run_role_operation)
    return m


@pytest.fixture
def fixed_now():
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def store_path(tmp_path) -> Path:
    return tmp_path / "schedules.json"


@pytest.fixture
def tracker():
    return LatencyTracker(default=25.0, window=20)


@pytest.fixture
def service(store_path, mock_push, mock_loop, fixed_now, tracker):
    return SchedulerService(
        store_path=store_path,
        push_tool=mock_push,
        agent_loop=mock_loop,
        tracker=tracker,
        _now_fn=lambda: fixed_now,
    )


async def drain_tasks():
    """Let all pending asyncio tasks finish."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        done, still_pending = await asyncio.wait(pending, timeout=1.0)
        if still_pending:
            for task in still_pending:
                task.cancel()
            await asyncio.gather(*still_pending, return_exceptions=True)
        if done:
            await asyncio.gather(*done, return_exceptions=True)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None
    kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    asyncio.run(test_func(**kwargs))
    return True


# 插件测试夹具所在目录；夹具保持旧的扁平布局（旧 PluginManager 的回归测试要求
# 它们原样通过），由下面的助手在测试里重整成新内核要求的 backend/ 形状。
PLUGIN_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "plugins"


def stage_plugin_fixture(name: str, dest_root: Path) -> Path:
    """把扁平布局的测试夹具就地重整成内核要求的 `<id>/backend/` 布局。

    `tests/fixtures/plugins/` 服务的是旧 `PluginManager`（扁平 `plugin.py`），
    而 spec 要求那批存量测试**原样**通过，作为「迁移未破坏行为」的证据，所以
    夹具本身保持旧形状。新内核要求 backend/ 布局，由这里重整，避免同一份夹具
    在仓库里留两份逐字重复、日后必然分叉的副本。#184 删除旧系统后，夹具可以
    直接改成新布局，这个函数随之删除。

    只把 Python 源码（`*.py` 与含 `__init__.py` 的 Python 子包）下沉到
    `backend/`；其余一律留在包根——`manifest.yaml`、`plugin.disabled`、
    `_conf_schema.json` 这类包级文件是已知例子，但白名单方式在新增夹具文件
    时必须逐个更新，稍不注意就会把 `.kv.json` 这类非后端代码也错误下沉（曾经
    发生：`counter/.kv.json` 被当成后端代码搬进 `backend/`，夹具静默失真且
    不报错）。反过来按"是不是 Python 代码"判断更不容易漏。`__pycache__` 直接
    跳过，不管在包根还是子目录里。
    """

    target = dest_root / name
    shutil.copytree(PLUGIN_FIXTURES_DIR / name, target, ignore=shutil.ignore_patterns("__pycache__"))
    backend = target / "backend"
    backend.mkdir(exist_ok=True)
    for item in sorted(target.iterdir()):
        if item.name == "backend":
            continue
        if _is_python_source(item):
            shutil.move(str(item), str(backend / item.name))
    return target


def _is_python_source(item: Path) -> bool:
    """判断一个包根条目是否属于后端 Python 代码，需要下沉到 `backend/`。"""

    if item.is_file():
        return item.suffix == ".py"
    if item.is_dir():
        return (item / "__init__.py").exists()
    return False
