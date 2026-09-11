"""Generic role draft transaction coverage, independent of plugin schemas."""

from pathlib import Path

import pytest

from core.roles.store import RoleStore


def test_role_and_plugin_draft_have_one_commit_point(tmp_path, monkeypatch):
    store = RoleStore(tmp_path)
    store.create_role(role_id="role", name="Before", system_prompt="test")

    def write(role_id, draft, data):
        data[role_id] = dict(draft)

    dispose = store.extensions.register(
        "sample", write, lambda role_id, data: data.get(role_id, {})
    )
    before = store.manifest_path.read_bytes()
    replace = Path.replace

    def fail(path, target):
        if target == store.manifest_path:
            raise OSError("disk unavailable")
        return replace(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail)
        with pytest.raises(OSError, match="disk unavailable"):
            store.update_role(
                "role", name="After", plugin_drafts={"sample": {"value": True}}
            )
    assert store.manifest_path.read_bytes() == before
    assert store.extensions.project("role") == {"sample": {}}
    store.update_role("role", name="After", plugin_drafts={"sample": {"value": True}})
    assert store.extensions.project("role") == {"sample": {"value": True}}
    assert store.get_role("role").name == "After"
    dispose()
    with pytest.raises(ValueError, match="角色扩展不可用"):
        store.update_role("role", name="Rejected", plugin_drafts={"sample": {}})
    assert store.get_role("role").name == "After"
    store.update_role("role", description="unrelated edit while disabled")
    assert store.extensions.read("sample") == {"role": {"value": True}}
