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


def test_legacy_fields_are_mapped_to_profile() -> None:
    profile = RoleProfile.from_legacy(system_prompt="规则", background="背景")

    assert profile.character.profile == "背景"
    assert profile.character.behavior_rules == "规则"
    assert RoleKnowledgeBase.from_dict(None).enabled is True


def test_knowledge_entry_round_trips_title_and_accepts_legacy_name() -> None:
    entry = RoleKnowledgeEntry.from_dict({"name": "旧标题", "content": "内容"})

    assert entry.title == "旧标题"
    assert entry.to_dict()["title"] == "旧标题"
