from pydantic import BaseModel

from agent.plugins import Plugin


class NullableConfigModel(BaseModel):
    """可空但默认值非空的字段：null 在 TOML 里没有对应表达形式。"""

    label: str | None = "default-label"


class NullableConfigPlugin(Plugin):
    name = "nullable_config"
    version = "0.1.0"
    ConfigModel = NullableConfigModel
