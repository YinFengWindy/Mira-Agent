import json

import pytest

from core.scene.state import SceneStateStore


@pytest.mark.parametrize("source_index", [0, 1, 2])
def test_legacy_state_is_imported_only_by_live_write_and_not_resurrected(
    tmp_path, source_index
):
    roots = (tmp_path / "package", tmp_path / "old-package")
    sources = (
        tmp_path / "plugins" / "scene_awareness" / "kv.json",
        *(root / "scene_awareness" / ".kv.json" for root in roots),
    )
    source = sources[source_index]
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "scene_awareness_sessions": {
                    "role:mira": {"scene_key": "rain", "visual_key": "umbrella"}
                },
                "other": 7,
            }
        ),
        encoding="utf-8",
    )
    state = SceneStateStore(tmp_path, roots)
    assert not state.path.exists()
    assert (
        state.get("scene_awareness_sessions")["role:mira"]["visual_key"] == "umbrella"
    )
    state.set("scene_awareness_sessions", {})
    assert source.exists()
    loaded = SceneStateStore(tmp_path, roots)
    assert loaded.get("scene_awareness_sessions") == {}
    assert loaded.get("other") == 7


def test_existing_target_and_current_disk_updates_win_over_legacy(tmp_path):
    state = SceneStateStore(tmp_path)
    state.set("scene_awareness_sessions", {"first": 1})
    candidate = SceneStateStore(tmp_path)
    state.set("scene_awareness_sessions", {"newer": 2})
    assert candidate.get("scene_awareness_sessions") == {"newer": 2}
