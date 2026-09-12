from __future__ import annotations

import re

_IDENTITY_MACRO = re.compile(r"\{\{(char|user)\}\}", re.IGNORECASE)


def expand_role_macros(
    text: str, *, role_name: str, nickname: str = "", user_name: str = ""
) -> str:
    """Expand supported identity macros once, leaving other card macros intact."""
    values = {
        "char": nickname.strip() or role_name.strip(),
        "user": user_name.strip() or "用户",
    }
    return _IDENTITY_MACRO.sub(lambda match: values[match.group(1).lower()], text)
