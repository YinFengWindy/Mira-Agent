import pytest

from core.roles.model_updates import prepare_role_model_updates
from core.roles.store import RoleStore


def test_model_update_preserves_current_non_model_fields(tmp_path):
    store = RoleStore(tmp_path)
    role = store.create_role(
        name="role", system_prompt="prompt", runtime_config={"custom": "current"}
    )
    payload = prepare_role_model_updates(
        store,
        [
            {
                "role_id": role.id,
                "runtime_config": {
                    "dialogue_model_registration_id": "new",
                    "custom": "stale",
                },
            }
        ],
        {"new"},
    )
    assert payload["roles"][0]["runtime_config"]["custom"] == "current"
    assert (
        payload["roles"][0]["runtime_config"]["dialogue_model_registration_id"] == "new"
    )
    assert not store.get_role(role.id).runtime_config["dialogue_model_registration_id"]


def test_invalid_binding_does_not_write_any_role(tmp_path):
    store = RoleStore(tmp_path)
    role = store.create_role(name="role", system_prompt="prompt")
    before = store.manifest_path.read_bytes()
    with pytest.raises(ValueError, match="不存在"):
        prepare_role_model_updates(
            store,
            [
                {
                    "role_id": role.id,
                    "runtime_config": {"dialogue_model_registration_id": "missing"},
                }
            ],
            set(),
        )
    assert store.manifest_path.read_bytes() == before
