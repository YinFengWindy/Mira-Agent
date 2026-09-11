from core.roles.migration import migrate_manifest_payload


def test_manifest_v2_migration_is_idempotent_and_preserves_legacy_fields() -> None:
    payload, changed = migrate_manifest_payload(
        {
            "version": 2,
            "roles": [
                {
                    "id": "mira",
                    "system_prompt": "规则",
                    "background": "背景",
                    "runtime_config": {"dialogue_model_effort": "high"},
                }
            ],
        }
    )

    assert changed is True
    assert payload["version"] == 4
    role = payload["roles"][0]
    assert role["profile"]["character"]["profile"] == "背景"
    assert role["runtime_config"] == {"dialogue_model_effort": "high"}

    normalized, changed_again = migrate_manifest_payload(payload)
    assert changed_again is False
    assert normalized == payload
