from agent.core.runtime_support import (
    LLMServices,
    MemoryConfig,
    MemoryServices,
    ToolDiscoveryState,
)


def test_tool_discovery_state_evicts_oldest_tool_beyond_capacity():
    state = ToolDiscoveryState(capacity=2)
    state.update("cli:1", ["tool_a", "tool_b"], {"always"})
    assert state.get_preloaded("cli:1") == {"tool_a", "tool_b"}
    assert state.get_preloaded_ordered("cli:1") == ["tool_a", "tool_b"]

    state.update("cli:1", ["tool_a"], {"always"})
    state.update("cli:1", ["tool_c"], {"always"})

    assert state.get_preloaded("cli:1") == {"tool_a", "tool_c"}
    assert state.get_preloaded_ordered("cli:1") == ["tool_a", "tool_c"]
    assert "tool_b" not in state.get_preloaded("cli:1")


def test_tool_discovery_state_skips_always_on_and_tool_search():
    state = ToolDiscoveryState()
    state.update(
        "cli:1", ["always_tool", "tool_search", "hidden_tool"], {"always_tool"}
    )

    assert state.get_preloaded("cli:1") == {"hidden_tool"}


def test_unlock_from_result_extracts_matched_names():
    state = ToolDiscoveryState()

    unlocked = state.unlock_from_result(
        '{"matched": [{"name": "shell"}, {"name": "web_search"}]}'
    )

    assert unlocked == {"shell", "web_search"}


def test_unlock_from_result_returns_empty_set_for_empty_matched():
    assert ToolDiscoveryState().unlock_from_result('{"matched": []}') == set()


def test_unlock_from_result_does_not_raise_on_invalid_json():
    assert ToolDiscoveryState().unlock_from_result("not-json") == set()


def test_unlock_from_result_skips_items_without_usable_name():
    state = ToolDiscoveryState()

    assert (
        state.unlock_from_result('{"matched": [{"summary": "no name here"}]}') == set()
    )
    assert state.unlock_from_result('{"matched": [{"name": ""}]}') == set()


def test_service_containers_hold_injected_objects():
    llm = LLMServices(provider=object(), light_provider=object())
    memory = MemoryServices(engine=object())
    config = MemoryConfig(window=12)

    assert llm.provider is not None
    assert memory.engine is not None
    assert config.window == 12
