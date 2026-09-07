from agent.config_models import Config


def test_explicit_empty_registry_is_not_replaced_by_legacy_model():
    config = Config(provider="openai", model="legacy", api_key="key", model_registrations=[])
    assert config.model_registrations == []


def test_legacy_constructor_still_registers_an_explicit_model():
    config = Config(provider="openai", model="legacy", api_key="key")
    assert len(config.model_registrations) == 1
    assert config.model_registrations[0].model == "legacy"
    assert Config(provider="", model="", api_key="").model_registrations == []
