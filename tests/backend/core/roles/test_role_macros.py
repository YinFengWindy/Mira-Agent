from core.roles.role_macros import expand_role_macros


def test_macros_use_nickname_and_explicit_user_context() -> None:
    assert (
        expand_role_macros(
            "{{CHAR}}认识{{user}}", role_name="Shiori", nickname="栞", user_name="风"
        )
        == "栞认识风"
    )


def test_macro_defaults_and_unknown_macros_preserve_literal_text() -> None:
    assert (
        expand_role_macros("{{char}}认识{{user}}，{{unknown}}", role_name="Shiori")
        == "Shiori认识用户，{{unknown}}"
    )


def test_macro_expansion_does_not_reinterpret_user_supplied_names() -> None:
    assert (
        expand_role_macros(
            "{{char}}认识{{user}}", role_name="{{user}}", user_name="小明"
        )
        == "{{user}}认识小明"
    )
