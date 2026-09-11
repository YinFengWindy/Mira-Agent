from pathlib import Path

from plugins.akasha.backend.core import SourceMessage
from plugins.akasha.backend.store import AkashaStore
from plugins.akasha.backend.replay_inputs import (
    iter_replay_turns,
    load_embeddings_from_cache,
    skip_message,
)


def test_load_embeddings_from_cache_counts_hits_and_misses(
    tmp_path: Path,
) -> None:
    store = AkashaStore(tmp_path / "akasha.db")
    messages = [
        SourceMessage("s:0", "s", 0, "user", "已缓存", "2026-01-01T00:00:00+00:00"),
        SourceMessage(
            "s:1", "s", 1, "assistant", "新消息", "2026-01-01T00:00:01+00:00"
        ),
    ]
    try:
        store.upsert_cached_embedding(
            message=messages[0],
            model="m",
            embedding=[1.0, 0.0],
        )

        embeddings, hits, misses = load_embeddings_from_cache(
            store=store,
            model="m",
            messages=messages,
        )
    finally:
        store.close()

    assert hits == 1
    assert misses == 1
    assert embeddings == {"s:0": [1.0, 0.0]}


def test_akasha_rebuild_skips_scheduler_messages() -> None:
    scheduler_user = SourceMessage(
        "scheduler:job:0",
        "scheduler:job",
        0,
        "user",
        "查询北京天气",
        "2026-01-01T00:00:00+00:00",
    )
    normal_user = SourceMessage(
        "telegram:1:0",
        "telegram:1",
        0,
        "user",
        "今天聊 Akasha",
        "2026-01-01T00:00:01+00:00",
    )

    assert skip_message(scheduler_user, set()) is True
    assert skip_message(normal_user, set()) is False
    assert list(iter_replay_turns([scheduler_user, normal_user], set())) == [
        [normal_user]
    ]
