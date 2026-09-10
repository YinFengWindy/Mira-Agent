from enum import Enum

from pydantic import BaseModel

from agent.plugins import Plugin


class Mode(Enum):
    """刻意不继承 str：这样 Enum 实例本身无法直接过 json.dumps。"""

    QUIET = "quiet"
    LOUD = "loud"


class NullableConfigModel(BaseModel):
    """两个刁钻默认值：null 在 TOML 里无表达形式，Enum 不能直接过 JSON 传输。"""

    label: str | None = "default-label"
    mode: Mode = Mode.QUIET


class NullableConfigPlugin(Plugin):
    name = "nullable_config"
    version = "0.1.0"
    ConfigModel = NullableConfigModel
