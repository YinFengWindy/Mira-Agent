from unittest.mock import AsyncMock, MagicMock

from agent.config_models import Config
from bootstrap.providers import build_providers


def test_bootstrap_providers_set_a_shared_request_budget(monkeypatch):
    provider = MagicMock(aclose=AsyncMock())
    create_provider = MagicMock(return_value=provider)
    monkeypatch.setattr("bootstrap.providers.LLMProvider", create_provider)
    config = Config(
        provider="openai",
        model="main",
        api_key="main-key",
        base_url="https://example.com/v1",
        light_model="light",
        light_api_key="light-key",
        light_base_url="https://light.example.com/v1",
        agent_model="agent",
        agent_api_key="agent-key",
        agent_base_url="https://agent.example.com/v1",
        multimodal=False,
    )

    main, light, agent = build_providers(config)

    create_provider.assert_called_once()
    assert create_provider.call_args.kwargs["request_timeout_s"] == 45.0
    assert create_provider.call_args.kwargs["stream_idle_timeout_s"] == 45.0
    assert create_provider.call_args.kwargs["api_key"] == "main-key"
    assert main is provider
    assert light is None and agent is None
