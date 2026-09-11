"""Plugin-owned input selection and cached vectors for Akasha replay."""

from __future__ import annotations

from collections.abc import Iterator

from .core import SourceMessage
from .store import AkashaStore


def skip_session_key(session_key: str) -> bool:
    """Identifies scheduler-only sessions excluded from memory replay."""
    return session_key.startswith("scheduler:")


def skip_message(message: SourceMessage, skip_message_ids: set[str]) -> bool:
    """Filters explicit exclusions and background-only messages."""
    return (
        message.id in skip_message_ids
        or skip_session_key(message.session_key)
        or message.content.startswith("[后台任务完成]")
    )


def load_embeddings_from_cache(
    *,
    store: AkashaStore,
    model: str,
    messages: list[SourceMessage],
) -> tuple[dict[str, list[float]], int, int]:
    """Loads replay vectors and returns exact cache hit and miss counts."""
    embedding_map: dict[str, list[float]] = {}
    cache_hits = 0
    cache_misses = 0
    for message in messages:
        embedding = store.get_cached_embedding(message=message, model=model)
        if embedding is None:
            cache_misses += 1
        else:
            cache_hits += 1
            embedding_map[message.id] = embedding
    return embedding_map, cache_hits, cache_misses


def iter_replay_turns(
    messages: list[SourceMessage],
    skip_message_ids: set[str],
) -> Iterator[list[SourceMessage]]:
    """Groups eligible user messages with their following assistant response."""
    by_turn = {
        (message.session_key, message.seq, message.role): message
        for message in messages
        if not skip_message(message, skip_message_ids)
    }
    used: set[str] = set()
    for message in messages:
        if message.id in used or skip_message(message, skip_message_ids):
            continue
        if message.role != "user":
            continue
        turn = [message]
        used.add(message.id)
        assistant = by_turn.get((message.session_key, message.seq + 1, "assistant"))
        if assistant is not None and assistant.id not in used:
            turn.append(assistant)
            used.add(assistant.id)
        yield turn
