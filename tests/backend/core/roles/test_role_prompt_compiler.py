from core.roles.profile_models import (
    RoleCharacterDefinition,
    RoleKnowledgeBase,
    RoleKnowledgeEntry,
    RoleProfile,
)
from core.roles.role_prompt_compiler import RoleKnowledgeMatcher, RolePromptCompiler


def test_compiler_uses_stable_profile_order_and_mood_contract() -> None:
    profile = RoleProfile(
        character=RoleCharacterDefinition(
            profile="资料",
            personality="性格",
            behavior_rules="规则",
        )
    )
    entry = RoleKnowledgeEntry(content="知识")
    result = RolePromptCompiler().compile(
        profile,
        [entry],
        {"mood_catalog": ["平静"], "default_mood": "平静"},
    )

    assert result.content.index("[role_profile]") < result.content.index("[role_personality]")
    assert result.content.index("[role_personality]") < result.content.index("[role_behavior_rules]")
    assert result.content.index("[role_behavior_rules]") < result.content.index("[role_knowledge]")
    assert "Mood Output Contract" in result.content


def test_knowledge_matcher_respects_case_and_budget() -> None:
    knowledge = RoleKnowledgeBase(
        token_budget=1,
        entries=[
            RoleKnowledgeEntry(
                id="always",
                content="常驻",
                always_active=True,
                priority=10,
                insertion_order=1,
            ),
            RoleKnowledgeEntry(
                id="keyword",
                content="命中内容很长",
                primary_keys=["Mira"],
                case_sensitive=False,
                insertion_order=2,
            ),
        ],
    )

    matched = RoleKnowledgeMatcher().match(knowledge, "mira")
    assert [entry.id for entry in matched] == ["always"]
