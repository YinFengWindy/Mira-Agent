from __future__ import annotations

import asyncio
import shutil
import tempfile
import threading
from pathlib import Path

import pytest

from agent.plugin_host import HostServices, PluginKernel
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus
from core.roles.store import RolePetPackage, RoleStore

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_desktop_pet_plugin(*, services: HostServices) -> PluginKernel:
    """Loads a fresh copy of the plugin package through the real v2 kernel.

    Same pattern as ``plugins/novelai/tests/test_plugin.py``: copying into a
    throwaway directory gives each test its own ``import_path``, so tests never
    collide through ``sys.modules`` caching.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = Path(tmp) / "desktop_pet"
        shutil.copytree(PLUGIN_DIR, plugin_dir)
        kernel = PluginKernel([Path(tmp)], services=services)
        asyncio.run(kernel.load_all())
        return kernel


def _services(tmp_path: Path, role_store: RoleStore | None = None) -> HostServices:
    # `role_store` is handed in rather than built from `workspace`, mirroring
    # `bootstrap/tools.py`: the plugin must get the host's *one* instance,
    # because the role write lock is per-instance (see manifest.py's
    # `role_store` note). A test that let the plugin build its own would pass
    # while reproducing exactly the bug the capability exists to prevent.
    return HostServices(
        event_bus=EventBus(),
        tool_registry=ToolRegistry(),
        workspace=tmp_path,
        role_store=role_store or RoleStore(tmp_path),
    )


def _bind_pet(
    workspace: Path,
    *,
    enabled: bool = True,
    with_file: bool = True,
    store: RoleStore | None = None,
) -> RoleStore:
    store = store or RoleStore(workspace)
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
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
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
    assert (
        Path(package["spritesheet_abs"])
        == (store.roles_dir / "assets/mira/pets/pet-1/spritesheet.webp").resolve()
    )


def test_binding_get_ignores_a_role_whose_pet_is_switched_off(tmp_path: Path) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, enabled=False, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    # A role keeps its package after the user switches the pet off; only
    # `desktop_pet_enabled` says whether to render it.
    assert asyncio.run(resolved[1]({})) == {"binding": None}


def test_binding_get_reports_nothing_when_the_spritesheet_is_missing(
    tmp_path: Path,
) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, with_file=False, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    assert asyncio.run(resolved[1]({})) == {"binding": None}


def test_binding_get_reports_nothing_when_no_role_has_a_pet(tmp_path: Path) -> None:
    store = RoleStore(tmp_path)
    _ = store.create_role(role_id="mira", name="Mira", system_prompt="test")
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
    resolved = kernel.rpc.resolve("plugin.desktop_pet.binding.get")
    assert resolved is not None

    assert asyncio.run(resolved[1]({})) == {"binding": None}


def _resolve(kernel: PluginKernel, method: str):
    resolved = kernel.rpc.resolve(f"plugin.desktop_pet.{method}")
    assert resolved is not None, method
    return resolved[1]


def test_a_plugin_write_waits_on_the_host_role_lock(tmp_path: Path) -> None:
    """The capability's whole reason for existing, asserted behaviourally.

    The role write lock is created per `RoleStore` instance
    (`RoleManifestRepository.__init__`), so "the plugin shares the host's lock"
    is only true if it got the host's *instance*. A plugin that built its own
    from `ctx.workspace` would read and write the same `roles.json` under a
    different lock, and two read-modify-write cycles would silently overwrite
    each other — `atomic_save_json` only makes a single write atomic.

    Identity (`granted is store`) would be the cheap assertion, but the lock is
    what actually protects the data, so that is what this pins.
    """
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
    select = _resolve(kernel, "pets.select")
    finished = threading.Event()

    def run_plugin_write() -> None:
        asyncio.run(select({"role_id": "mira", "package_id": "pet-1"}))
        finished.set()

    # Held from *this* thread: `RLock` is reentrant per thread, so the worker
    # below only blocks if it is genuinely the same lock object.
    with store.lock:
        worker = threading.Thread(target=run_plugin_write, daemon=True)
        worker.start()
        assert not finished.wait(timeout=0.3), (
            "the plugin wrote roles.json without waiting for the host's lock; "
            "it is holding its own RoleStore instance"
        )

    worker.join(timeout=5)
    assert (
        finished.is_set()
    ), "the plugin write never completed after the lock was released"


def test_pets_list_returns_the_rows_roles_list_used_to_carry(tmp_path: Path) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))

    result = asyncio.run(_resolve(kernel, "pets.list")({"role_id": "mira"}))

    assert result is not None
    assert result["selected_package_id"] == "pet-1"
    package = result["packages"][0]
    assert package["id"] == "pet-1"
    assert package["display_name"] == "Pet"
    # The two names the desktop grants `shiori-asset://` URLs for; they are the
    # contract, so they must match what `role_presenter` emitted.
    assert Path(package["spritesheet_abs"]).is_absolute()
    assert package["preview_abs"] is None


def test_pets_select_and_remove_go_through_the_shared_store(tmp_path: Path) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))

    after_remove = asyncio.run(
        _resolve(kernel, "pets.remove")({"role_id": "mira", "package_id": "pet-1"})
    )

    assert after_remove == {"selected_package_id": None, "packages": []}
    # Written through the host's own store, so the host sees it without a reload.
    role = store.get_role("mira")
    assert role is not None
    assert role.pet_packages == []
    # Removing the selected package also switches the pet off — that invariant
    # lives in `pet_state.replace_packages` and must survive the move.
    assert role.desktop_pet_enabled is False


def test_pet_rpc_requires_the_ids_it_acts_on(tmp_path: Path) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))

    for method, payload in [
        ("pets.list", {}),
        ("pets.import", {"role_id": "mira"}),
        ("pets.remove", {"role_id": "mira"}),
        ("pets.select", {"role_id": "mira"}),
        ("pets.select", {"package_id": "pet-1"}),
    ]:
        with pytest.raises((ValueError, KeyError)):
            asyncio.run(_resolve(kernel, method)(payload))


def test_every_pet_method_disappears_when_the_plugin_is_unloaded(
    tmp_path: Path,
) -> None:
    store = RoleStore(tmp_path)
    _bind_pet(tmp_path, store=store)
    kernel = _load_desktop_pet_plugin(services=_services(tmp_path, store))
    methods = ("binding.get", "pets.list", "pets.import", "pets.remove", "pets.select")
    for method in methods:
        assert kernel.rpc.resolve(f"plugin.desktop_pet.{method}") is not None, method

    asyncio.run(kernel.unload("desktop_pet"))

    for method in methods:
        assert kernel.rpc.resolve(f"plugin.desktop_pet.{method}") is None, method
