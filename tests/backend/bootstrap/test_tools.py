from __future__ import annotations

from pathlib import Path

import pytest

from bootstrap.tools import (
    _resolve_plugin_dirs,
    _role_owns_channel_target,
    _validate_role_target,
)
from core.roles import RoleRepository, RoleStore

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_resolve_plugin_dirs_uses_repository_root_in_dev(tmp_path: Path) -> None:
    dirs = _resolve_plugin_dirs(tmp_path)

    assert dirs == [_REPO_ROOT / "plugins"]
    assert dirs[0].is_dir()


def test_resolve_plugin_dirs_uses_meipass_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    dirs = _resolve_plugin_dirs(tmp_path)

    assert dirs == [tmp_path / "plugins"]


def test_role_target_validation_uses_canonical_chat_id_comparison(
    tmp_path: Path,
) -> None:
    store = RoleStore(tmp_path)
    role = store.create_role(
        role_id="mira",
        name="Mira",
        description="",
        system_prompt="You are Mira.",
    )
    store.update_role(
        role.id,
        channel_bindings=[
            {"channel": "qq", "chat_id": "gqq:42", "allow_from": ["user-1"]}
        ],
    )

    assert _role_owns_channel_target(
        RoleRepository(store),
        role_id=role.id,
        channel="qq",
        chat_id="42",
    )


def test_role_target_validation_explains_wrong_channel_for_bound_chat(
    tmp_path: Path,
) -> None:
    store = RoleStore(tmp_path)
    role = store.create_role(
        role_id="mira",
        name="Mira",
        description="",
        system_prompt="You are Mira.",
    )
    store.update_role(
        role.id,
        channel_bindings=[
            {
                "channel": "qqbot",
                "chat_id": "c2c:user-1",
                "allow_from": ["user-1"],
            }
        ],
    )

    result = _validate_role_target(
        RoleRepository(store),
        role_id=role.id,
        channel="qq",
        chat_id="c2c:user-1",
    )

    assert isinstance(result, str)
    assert "已绑定渠道 qqbot" in result
    assert "请使用 channel=qqbot" in result
