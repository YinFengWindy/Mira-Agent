from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .models import RoleRecord
from .knowledge_matcher import RoleKnowledgeMatcher
from .profile_models import RoleKnowledgeEntry, RoleProfile
from .role_macros import expand_role_macros


@dataclass(frozen=True)
class CompiledRolePrompt:
    """Stable role prompt output consumed by passive and proactive turns."""

    content: str
    matched_knowledge_entries: tuple[RoleKnowledgeEntry, ...] = ()


class RolePromptCompiler:
    """Compiles a RoleProfile into one ordered runtime prompt."""

    def __init__(self, matcher: RoleKnowledgeMatcher | None = None) -> None:
        self.matcher = matcher or RoleKnowledgeMatcher()

    def compile(
        self,
        profile: RoleProfile | RoleRecord,
        matched_knowledge_entries: Iterable[RoleKnowledgeEntry] | None = None,
        runtime_context: dict[str, Any] | None = None,
        *,
        role_name: str = "",
        user_name: str = "",
    ) -> CompiledRolePrompt:
        """Render stable definitions, selected knowledge, and runtime output constraints."""
        if isinstance(profile, RoleRecord):
            role_name = role_name or profile.name or profile.id
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
        if definition.response_constraints:
            blocks.append(
                f"[role_response_constraints]\n{definition.response_constraints}"
            )
        content = expand_role_macros(
            "\n\n".join(blocks),
            role_name=role_name,
            nickname=definition.nickname,
            user_name=user_name,
        )
        if role_name.strip():
            content = "\n\n".join(
                part
                for part in (f"[role_identity]\n{role_name.strip()}", content)
                if part
            )
        mood_contract = _build_mood_contract(runtime_context or {})
        if mood_contract:
            content = "\n\n".join(part for part in (content, mood_contract) if part)
        return CompiledRolePrompt(content=content, matched_knowledge_entries=entries)


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
