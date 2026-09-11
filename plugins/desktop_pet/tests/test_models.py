"""Persisted pet-state validation is owned by the plugin model."""

from plugins.desktop_pet.backend.models import RolePetPackage, RolePetState


def test_foreign_or_missing_selection_cannot_restore_enabled_pet():
    package = RolePetPackage(
        "pet",
        "codex-sprite@1",
        "Pet",
        "assets/mira/pets/pet/pet.json",
        "assets/mira/pets/pet/spritesheet.webp",
        "today",
    )
    for selected in ("another-package", None):
        state = RolePetState.from_dict(
            "mira",
            {
                "pet_packages": [package.to_dict()],
                "selected_pet_package_id": selected,
                "desktop_pet_enabled": True,
            },
        )
        assert state.selected_pet_package_id is None
        assert state.desktop_pet_enabled is False
        assert state.pet_packages == [package]
    restored = RolePetState.from_dict(
        "mira",
        {
            "pet_packages": [package.to_dict()],
            "selected_pet_package_id": "pet",
            "desktop_pet_enabled": True,
        },
    )
    assert restored.desktop_pet_enabled is True
    assert RolePetState.from_dict("mira", restored.to_dict()) == restored
