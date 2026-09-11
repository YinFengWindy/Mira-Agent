from __future__ import annotations

from pydantic import BaseModel, Field


class NovelAIConfig(BaseModel):
    """``[plugins.novelai]`` config schema: validated via ``plugin.config.*``.

    Field names and defaults mirror ``NovelAISettings`` (the frozen dataclass
    the runtime service actually consumes) exactly, so ``setup()`` can build a
    ``NovelAISettings`` straight off this model's ``model_dump()`` without a
    second, drift-prone copy of the defaults.
    """

    # enabled 属于宿主插件管理；配置表单只声明生图参数，避免覆盖启停状态。
    token: str = Field(default="", description="NovelAI API token")
    base_url: str = "https://image.novelai.net"
    default_model: str = "nai-diffusion-4-5-curated"
    nsfw_model: str = "nai-diffusion-4-5-full"
    nsfw_enabled: bool = False
    allow_txt2img: bool = True
    allow_img2img: bool = True
    auto_writeback_role_assets: bool = False
    max_pixels: int = 1024 * 1024
    max_steps: int = 28
    default_samples: int = 1
    add_quality_tags: bool = False
    undesired_content_preset: int = 0
