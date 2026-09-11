from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from agent.plugin_host import HostServices, PluginKernel
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus
from core.roles.store import RolePetPackage, RoleStore

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_desktop_pet_plugin(*, services: HostServices) -> PluginKernel:
    """Loads a fresh copy of the plugin package through the real v2 kernel.

    Same pattern as ``plugins/novelai/tests/test_plugin.py``: copying into a
    throwaway directory gives each test its own ``import_path``, so tests never
    collide through ``sys.modules`` caching.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = Path(tmp) / "desktop_pet"
        shutil.copytree(_REPO_ROOT / "plugins" / "desktop_pet", plugin_dir)
        kernel = PluginKernel([Path(tmp)], services=services)
        asyncio.run(kernel.load_all())
        return kernel


def _services(tmp_path: Path) -> HostServices:
    return HostServices(
        event_bus=EventBus(),
        tool_registry=ToolRegistry(),
        workspace=tmp_path,
    )


def _bind_pet(workspace: Path, *, enabled: bool = True, with_file: bool = True) -> RoleStore:
    store = RoleStore(workspace)
    role = store.create_role(role_id="mira", name="Mira", system_prompt="test")
    spritesheet = "assets/mira/pets/pet-1/spritesheet.webp"
    store.replace_pet_packages(
        role.id,
        [
            RolePetPackage(
                id="pet-1",
                format="codex-sprite@1",
                display_name="Pet",
                manifest_path="assets/mira/pets/pet-1/pet.json",
                spritesheet_path=spritesheet,
                imported_at="2026-07-25T00:00:00+08:00",
                actions={"greeting": "waving"},
            )
        ],
    )
    store.select_pet_package(role.id, "pet-1")
    store.update_role(role.id, desktop_pet_enabled=enabled)
    if with_file:
        target = store.roles_dir / spritesheet
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(b"not-a-real-webp")
    return store


def test_plugin_registers_tool_and_rpc_and_both_disappear_on_unload(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    kernel = _load_desktop_pet_plugin(services=services)

    assert services.tool_registry is not None
    assert services.tool_registry.has_tool("pet_action") is True
    assert kernel.rpc.resolve("plugin.desktop_pet.binding.get") is not None

    asyncio.run(kernel.unload("desktop_pet"))

    assert services.tool_registry.has_tool("pet_action") is False
    assert kernel.rpc.resolve("plugin.desktop_pet.binding.get") is None


def test_binding_get_returns_the_selected_package(tmp_path: Path) -> None:
    store = _bind_pet(tmp_path)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    result = asyncio.run(resolved[1]({}))

    assert result is not None
    binding = result["binding"]
    assert binding is not None
    assert binding["role_id"] == "mira"
    assert binding["actions"] == {"greeting": "waving"}
    package = binding["package"]
    assert package["id"] == "pet-1"
    assert package["display_name"] == "Pet"
    # Absolute, and named `spritesheet_abs` so the desktop bridge grants it a
    # `shiori-asset://` URL on the way to the renderer.
    assert Path(package["spritesheet_abs"]) == (
        store.roles_dir / "assets/mira/pets/pet-1/spritesheet.webp"
    ).resolve()


def test_binding_get_ignores_a_role_whose_pet_is_switched_off(tmp_path: Path) -> None:
    _bind_pet(tmp_path, enabled=False)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    # A role keeps its package after the user switches the pet off; only
    # `desktop_pet_enabled` says whether to render it.
    assert asyncio.run(resolved[1]({})) == {"binding": None}


def test_binding_get_reports_nothing_when_the_spritesheet_is_missing(
    tmp_path: Path,
) -> None:
    _bind_pet(tmp_path, with_file=False)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    assert asyncio.run(resolved[1]({})) == {"binding": None}


def test_binding_get_reports_nothing_when_no_role_has_a_pet(tmp_path: Path) -> None:
    _ = RoleStore(tmp_path).create_role(role_id="mira", name="Mira", system_prompt="test")
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    assert asyncio.run(resolved[1]({})) == {"binding": None}
