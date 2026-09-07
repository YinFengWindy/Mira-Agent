import pytest

from core.roles.knowledge_matcher import RoleKnowledgeMatcher
from core.roles.profile_models import RoleKnowledgeBase, RoleKnowledgeEntry


def test_matching_keeps_all_content_without_a_budget() -> None:
    entries = [
        RoleKnowledgeEntry(id="long", content="长" * 10000, always_active=True),
        RoleKnowledgeEntry(id="keyword", content="补充" * 5000, primary_keys=["rain"]),
    ]

    matched = RoleKnowledgeMatcher().match(RoleKnowledgeBase(enabled=True, entries=entries), "rain")

    assert {entry.id for entry in matched} == {"long", "keyword"}
    assert sum(len(entry.content) for entry in matched) == 20000


@pytest.mark.parametrize(
    ("primary", "secondary", "text", "case_sensitive", "expected"),
    [
        (["Rain", "Snow"], [], "rain", False, True),
        (["Rain"], [], "rain", True, False),
        (["Rain"], [], "Rain", True, True),
        (["rain"], ["night", "morning"], "rain in the morning", False, True),
        (["rain"], ["night"], "rain", False, False),
        (["rain"], ["night"], "night", False, False),
        ([], ["night"], "night", False, False),
        (["", " "], [], " ", False, False),
    ],
)
def test_primary_keys_trigger_and_secondary_keys_refine(
    primary: list[str], secondary: list[str], text: str, case_sensitive: bool, expected: bool
) -> None:
    entry = RoleKnowledgeEntry(
        content="matched",
        primary_keys=primary,
        secondary_keys=secondary,
        case_sensitive=case_sensitive,
    )
    matched = RoleKnowledgeMatcher().match(RoleKnowledgeBase(enabled=True, entries=[entry]), text)

    assert bool(matched) is expected


def test_filters_disabled_and_empty_entries_and_orders_remaining_entries() -> None:
    knowledge = RoleKnowledgeBase(enabled=True, entries=[
        RoleKnowledgeEntry(id="disabled", content="hidden", always_active=True, enabled=False),
        RoleKnowledgeEntry(id="empty", content=" \n ", always_active=True),
        RoleKnowledgeEntry(id="b", content="B", always_active=True, insertion_order=2),
        RoleKnowledgeEntry(id="a", content="A", always_active=True, insertion_order=2),
        RoleKnowledgeEntry(id="first", content="first", always_active=True, insertion_order=1),
        RoleKnowledgeEntry(id="priority", content="priority", always_active=True, priority=2),
    ])

    assert [entry.id for entry in RoleKnowledgeMatcher().match(knowledge)] == [
        "priority", "first", "a", "b"
    ]
    knowledge.enabled = False
    assert RoleKnowledgeMatcher().match(knowledge) == []
