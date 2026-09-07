from unittest.mock import Mock

from core.roles.memory_service import RoleMemoryService
from core.roles.store import RoleStore


def test_deferred_initialization_preserves_existing_self_document(tmp_path):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    generator = Mock()
    memory = RoleMemoryService(tmp_path, self_seed_generator=generator, model_available=lambda role_id: False)
    root = memory.ensure_initialized(role)
    self_path = root / "SELF.md"
    self_path.write_text("# 我是谁\n\n自定义角色记忆", encoding="utf-8")
    role.memory_init_state = {"seed_self_ready": True, "seed_first_impression_ready": True}

    memory.seed_role_memory(role)

    generator.generate.assert_not_called()
    assert self_path.read_text(encoding="utf-8") == "# 我是谁\n\n自定义角色记忆"
