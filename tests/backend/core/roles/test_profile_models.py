from core.roles.profile_models import (
    RoleKnowledgeBase,
    RoleKnowledgeEntry,
    RoleProfile,
)


def test_role_profile_round_trips_runtime_fields_without_source_noise() -> None:
    profile = RoleProfile.from_dict(
        {
            "version": 1,
            "character": {
                "profile": "海边的向导",
                "personality": "温柔",
                "behavior_rules": "回答简洁",
            },
            "greetings": {"default": "你好", "alternates": ["晚上好"]},
            "knowledge_base": {"enabled": True, "token_budget": 10, "entries": []},
            "source": {"creator": "discarded"},
            "compatibility": {"unsupported_rules": ["discarded"]},
        }
    )

    serialized = profile.to_dict()
    assert serialized["character"]["behavior_rules"] == "回答简洁"
    assert "greetings" not in serialized
    assert "source" not in serialized
    assert "compatibility" not in serialized
    assert "response_constraints" not in serialized
    assert "token_budget" not in serialized["knowledge_base"]


def test_legacy_fields_are_mapped_to_profile() -> None:
    profile = RoleProfile.from_legacy(system_prompt="规则", background="背景")

    assert profile.character.profile == "背景"
    assert profile.character.behavior_rules == "规则"
    assert profile.character.response_constraints == ""
    assert RoleKnowledgeBase.from_dict(None).enabled is False


def test_explicit_knowledge_enabled_and_raw_source_survive_round_trip() -> None:
    source = {"extensions": {"selectiveLogic": 2}, "scan_depth": 100}
    payload = {
        "enabled": True,
        "token_budget": 0,
        "raw_source": source,
        "entries": [{"content": "世界观", "raw_source": source}],
    }
    saved = RoleKnowledgeBase.from_dict(payload).to_dict()

    assert saved["enabled"] is True
    assert "token_budget" not in saved
    assert saved["raw_source"] == source
    assert saved["entries"][0]["raw_source"] == source
    saved["raw_source"]["extensions"]["selectiveLogic"] = 99
    assert source["extensions"]["selectiveLogic"] == 2


def test_profile_round_trips_constraints_nickname_and_attribution() -> None:
    provenance = {
        "format": "charx", "card_version": "3.0", "creator": "作者",
        "tags": ["科幻"], "source": ["https://example.test/card"],
        "created_at": 123, "updated_at": "2026-09-01", "imported_at": "2026-09-07",
    }
    profile = RoleProfile.from_dict({
        "character": {"response_constraints": "每次回答一句", "nickname": "小栞"},
        "import_provenance": provenance,
    })

    assert profile.to_dict()["import_provenance"] == provenance
    assert profile.character.nickname == "小栞"
    assert profile.character.response_constraints == "每次回答一句"


def test_knowledge_entry_round_trips_title() -> None:
    entry = RoleKnowledgeEntry.from_dict({"title": "标题", "content": "内容"})

    assert entry.title == "标题"
    assert entry.to_dict()["title"] == "标题"
