from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, Field, field_validator

from .channel import QQBotChannel

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext

_UNRESOLVED_ENV_RE = re.compile(r"^\$\{\w+\}$")


class QQBotGroupConfigModel(BaseModel):
    """Compatibility schema for the historical, currently disabled group mode."""

    group_openid: str = Field(
        default="",
        validation_alias=AliasChoices("group_openid", "groupOpenid"),
    )
    allow_from: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("allow_from", "allowFrom"),
    )
    require_at: bool = Field(
        default=True,
        validation_alias=AliasChoices("require_at", "requireAt"),
    )
    allow_proactive: bool = Field(
        default=False,
        validation_alias=AliasChoices("allow_proactive", "allowProactive"),
    )


class QQBotConfigModel(BaseModel):
    """Configuration for the official QQBot application credentials."""

    app_id: str = Field(
        default="",
        validation_alias=AliasChoices("app_id", "appId"),
    )
    client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("client_secret", "clientSecret"),
    )
    allow_from: list[str] = Field(default_factory=list)
    groups: list[QQBotGroupConfigModel] = Field(default_factory=list)

    @field_validator("app_id", "client_secret", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str:
        text = str(value or "").strip()
        return "" if _UNRESOLVED_ENV_RE.fullmatch(text) else text


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 qqbot：校验插件配置，凭据齐备时贡献官方 QQBot 渠道。

    行为对齐 legacy：QQBotConfigModel 校验失败时 setup() 直接抛出，交由内核的
    通用失败回滚处理，与旧 ``_load_plugin_config`` 在校验失败时跳过插件加载
    的语义一致；凭据缺失（非校验失败）则不贡献渠道，同样与旧 channels() 一致。
    """
    config = QQBotConfigModel.model_validate(ctx.config.as_dict())
    if not config.app_id or not config.client_secret:
        return
    ctx.channels.add(
        QQBotChannel(
            app_id=config.app_id,
            client_secret=config.client_secret,
            allow_from=config.allow_from,
            groups=config.groups,
        )
    )
