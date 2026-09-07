from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.roles.self_seed import LlmRoleSelfSeedGenerator
from core.roles import RoleStore


@pytest.mark.asyncio
async def test_self_seed_uses_the_role_dialogue_model_snapshot(tmp_path) -> None:
    selected_provider = SimpleNamespace(
        chat=AsyncMock(return_value=SimpleNamespace(content="# 角色自我认知"))
    )
    fallback_provider = SimpleNamespace(
        chat=AsyncMock(side_effect=AssertionError("fallback"))
    )
    activations: list[tuple[str, str]] = []

    class _RoleRuntimeRegistry:
        async def get(self, role_id: str):
            self.role_id = role_id
            return self

        @contextmanager
        def activate_model(self, purpose: str):
            activations.append((self.role_id, purpose))
            yield SimpleNamespace(provider=selected_provider, model="role-model")

    generator = LlmRoleSelfSeedGenerator(
        provider=fallback_provider,
        model="base-model",
        role_runtime_registry=_RoleRuntimeRegistry(),
    )
    role = RoleStore(tmp_path).create_role(
        role_id="mira",
        name="Mira",
        description="陪伴者",
        background="相识不久",
        system_prompt="用中文回复",
    )

    result = await generator.agenerate(role)

    assert result == "# 角色自我认知"
    assert activations == [("mira", "chat")]
    assert selected_provider.chat.await_args.kwargs["model"] == "role-model"
    fallback_provider.chat.assert_not_called()


@pytest.mark.asyncio
async def test_self_seed_compiles_stable_profile_without_transient_knowledge(tmp_path) -> None:
    provider = SimpleNamespace(chat=AsyncMock(return_value=SimpleNamespace(content="# 我是谁")))
    role = RoleStore(tmp_path).create_role(
        role_id="mira", name="Mira", system_prompt="旧提示词", background="旧背景",
        runtime_config={"mood_catalog": ["平静"]},
        profile={
            "character": {
                "profile": "{{char}}是{{user}}的向导", "personality": "温柔",
                "behavior_rules": "诚实", "response_constraints": "简洁", "nickname": "小栞",
            },
            "knowledge_base": {
                "enabled": True,
                "entries": [{"content": "当前聊天知识", "always_active": True}],
            },
        },
    )

    await LlmRoleSelfSeedGenerator(provider=provider, model="test").agenerate(role)

    prompt = provider.chat.await_args.kwargs["messages"][1]["content"]
    assert "小栞是用户的向导" in prompt
    assert "温柔" in prompt and "诚实" in prompt and "简洁" in prompt
    assert "旧提示词" not in prompt and "旧背景" not in prompt
    assert "当前聊天知识" not in prompt and "Mood Output Contract" not in prompt
