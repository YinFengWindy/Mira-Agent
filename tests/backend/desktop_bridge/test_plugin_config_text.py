"""merge_plugin_table：定位-替换式合并 [plugins.<id>]，其余文本必须逐字节不变。"""

from __future__ import annotations

import tomllib

from desktop_bridge.plugin_config_text import merge_plugin_table


def test_appends_a_new_table_when_missing():
    text = '[llm]\nmodel = "x"\n'

    result = merge_plugin_table(text, "demo", {"a": 1})

    assert result.startswith(text)
    parsed = tomllib.loads(result)
    assert parsed["plugins"]["demo"] == {"a": 1}
    assert parsed["llm"] == {"model": "x"}


def test_appends_to_an_empty_file():
    result = merge_plugin_table("", "demo", {"a": 1})

    assert tomllib.loads(result) == {"plugins": {"demo": {"a": 1}}}


def test_replaces_a_table_in_the_middle_of_the_file_and_preserves_the_rest():
    text = (
        "# top comment\n"
        "[llm]\n"
        'model = "x"\n'
        "\n"
        "[plugins.demo]\n"
        "a = 1\n"
        "old = true\n"
        "\n"
        "[plugins.other]\n"
        "z = 9\n"
        "\n"
        "[agent]\n"
        'foo = "bar"\n'
    )
    prefix = text[: text.index("[plugins.demo]")]
    suffix = text[text.index("[plugins.other]") :]

    result = merge_plugin_table(text, "demo", {"a": 2})

    # 目标表之前、之后的文本必须逐字节保留（含注释与不相关表）
    assert result.startswith(prefix)
    assert result.endswith(suffix)
    parsed = tomllib.loads(result)
    assert parsed["plugins"]["demo"] == {"a": 2}
    assert "old" not in parsed["plugins"]["demo"]
    assert parsed["plugins"]["other"] == {"z": 9}
    assert parsed["agent"] == {"foo": "bar"}


def test_replaces_a_table_at_the_end_of_the_file():
    text = '[llm]\nmodel = "x"\n\n[plugins.demo]\na = 1\n'
    prefix = text[: text.index("[plugins.demo]")]

    result = merge_plugin_table(text, "demo", {"a": 2, "b": "hi"})

    assert result.startswith(prefix)
    parsed = tomllib.loads(result)
    assert parsed["plugins"]["demo"] == {"a": 2, "b": "hi"}


def test_replaces_a_table_without_a_trailing_newline_in_the_source():
    text = '[llm]\nmodel = "x"\n\n[plugins.demo]\na = 1'

    result = merge_plugin_table(text, "demo", {"a": 3})

    parsed = tomllib.loads(result)
    assert parsed["plugins"]["demo"] == {"a": 3}


def test_replaces_own_subtables_but_leaves_siblings_untouched():
    text = (
        "[plugins.demo]\n"
        "a = 1\n"
        "\n"
        "[plugins.demo.sub]\n"
        "old = true\n"
        "\n"
        "[plugins.other]\n"
        "z = 9\n"
    )
    suffix = text[text.index("[plugins.other]") :]

    result = merge_plugin_table(text, "demo", {"a": 2, "sub": {"new": True}})

    assert result.endswith(suffix)
    parsed = tomllib.loads(result)
    assert parsed["plugins"]["demo"] == {"a": 2, "sub": {"new": True}}
    assert parsed["plugins"]["other"] == {"z": 9}


def test_rendered_values_round_trip_through_toml_parsing():
    values = {
        "text": "hello",
        "flag": False,
        "count": 7,
        "items": ["a", "b"],
        "nested": {"inner": 1.5},
    }

    result = merge_plugin_table("", "demo", values)

    assert tomllib.loads(result)["plugins"]["demo"] == values


def test_a_plugin_id_that_is_a_prefix_of_another_does_not_collide():
    text = (
        "[plugins.foo]\n"
        "value = 1\n"
        "\n"
        "[plugins.foobar]\n"
        "value = 2\n"
    )

    result = merge_plugin_table(text, "foo", {"value": 3})

    parsed = tomllib.loads(result)
    assert parsed["plugins"]["foo"] == {"value": 3}
    assert parsed["plugins"]["foobar"] == {"value": 2}
