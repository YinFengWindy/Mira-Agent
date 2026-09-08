from core.roles.memory_service import RoleMemoryService
from core.roles.store import RoleStore


def test_deferred_initialization_preserves_existing_self_document(tmp_path):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    memory = RoleMemoryService(tmp_path)
    root = memory.ensure_initialized(role)
    self_path = root / "SELF.md"
    self_path.write_text("# 我是谁\n\n自定义角色记忆", encoding="utf-8")
    role.memory_init_state = {"seed_self_ready": True, "seed_first_impression_ready": True}

    state = memory.prepare_memory(role)

    assert state["self_seed"]["status"] == "generated"
    assert self_path.read_text(encoding="utf-8") == "# 我是谁\n\n自定义角色记忆"
