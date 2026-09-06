from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .models import RoleRecord
from .profile_models import RoleKnowledgeBase, RoleKnowledgeEntry, RoleProfile


@dataclass(frozen=True)
class CompiledRolePrompt:
    """Stable role prompt output consumed by passive and proactive turns."""

    content: str
    matched_knowledge_entries: tuple[RoleKnowledgeEntry, ...] = ()


class RoleKnowledgeMatcher:
    """Matches enabled Lorebook entries with deterministic ordering and a char budget."""

    def match(
        self,
        knowledge_base: RoleKnowledgeBase,
        text: str = "",
    ) -> list[RoleKnowledgeEntry]:
        if not knowledge_base.enabled or knowledge_base.token_budget <= 0:
            return []
        matched: list[RoleKnowledgeEntry] = []
        for entry in knowledge_base.entries:
            if not entry.enabled or not entry.content.strip():
                continue
            if entry.always_active or self._matches(entry, text):
                matched.append(entry)
        matched.sort(key=lambda item: (-item.priority, item.insertion_order, item.id))
        budget_chars = knowledge_base.token_budget * 4
        result: list[RoleKnowledgeEntry] = []
        used = 0
        for entry in matched:
            cost = len(entry.content)
            if result and used + cost > budget_chars:
                continue
            if not result and cost > budget_chars:
                result.append(entry)
                break
            result.append(entry)
            used += cost
        return result

    @staticmethod
    def _matches(entry: RoleKnowledgeEntry, text: str) -> bool:
        primary = [item for item in entry.primary_keys if item]
        secondary = [item for item in entry.secondary_keys if item]
        if not primary and not secondary:
            return False
        if entry.case_sensitive:
            haystack = text

            def contains(key: str) -> bool:
                return key in haystack
        else:
            haystack = text.casefold()

            def contains(key: str) -> bool:
                return key.casefold() in haystack
        # A primary key is required; secondary keys refine a match when present.
        if primary and not any(contains(key) for key in primary):
            return False
        return not secondary or any(contains(key) for key in secondary)


class RolePromptCompiler:
    """Compiles a RoleProfile into one ordered runtime prompt."""

    def __init__(self, matcher: RoleKnowledgeMatcher | None = None) -> None:
        self.matcher = matcher or RoleKnowledgeMatcher()

    def compile(
        self,
        profile: RoleProfile | RoleRecord,
        matched_knowledge_entries: Iterable[RoleKnowledgeEntry] | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> CompiledRolePrompt:
        if isinstance(profile, RoleRecord):
            if not (
                profile.profile.character.profile
                or profile.profile.character.personality
                or profile.profile.character.behavior_rules
            ):
                profile = RoleProfile.from_legacy(
                    system_prompt=profile.system_prompt,
                    background=profile.background,
                )
            else:
                profile = profile.profile
        definition = profile.character
        blocks: list[str] = []
        if definition.profile:
            blocks.append(f"[role_profile]\n{definition.profile}")
        if definition.personality:
            blocks.append(f"[role_personality]\n{definition.personality}")
        if definition.behavior_rules:
            blocks.append(f"[role_behavior_rules]\n{definition.behavior_rules}")
        entries = tuple(matched_knowledge_entries or ())
        if entries:
            blocks.append(
                "[role_knowledge]\n"
                + "\n\n".join(entry.content.strip() for entry in entries)
            )
        mood_contract = _build_mood_contract(runtime_context or {})
        if mood_contract:
            blocks.append(mood_contract)
        return CompiledRolePrompt(content="\n\n".join(blocks), matched_knowledge_entries=entries)


def _build_mood_contract(runtime_config: dict[str, Any]) -> str:
    raw_catalog = runtime_config.get("mood_catalog")
    if not isinstance(raw_catalog, list):
        return ""
    catalog = [str(item).strip() for item in raw_catalog if str(item).strip()]
    if not catalog:
        return ""
    default = str(runtime_config.get("default_mood") or "").strip() or catalog[0]
    return (
        "## Mood Output Contract\n"
        "你每次回复都必须输出一个 JSON 对象，不要输出 JSON 之外的解释、markdown 或代码块。\n"
        'JSON 结构固定为：{"content":"<角色回复正文>","mood":"<当前心情>"}\n'
        f"`mood` 只能从以下列表中选择一个：{'、'.join(catalog)}。\n"
        f"如果难以判断，请使用默认心情：{default}。"
    )
