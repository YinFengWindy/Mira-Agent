"""Legacy host tests model optional SDK boundaries without network calls."""

import sys
import types

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
