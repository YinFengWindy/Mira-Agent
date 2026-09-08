from core.memory.markdown_schema import DOCUMENT_DEFAULTS, render_memory_section
from core.roles.self_seed_state import resolve_self_seed_state, self_fingerprint
from core.roles.store import RoleStore


def test_known_legacy_defaults_retry_even_if_old_generator_marked_them_ready(tmp_path):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    role.memory_init_state = {"seed_self_ready": True}
    assert (
        resolve_self_seed_state(role, DOCUMENT_DEFAULTS["SELF.md"])["status"]
        == "pending"
    )
    assert (
        resolve_self_seed_state(role, "# 我是谁\n\n已生成的记忆")["status"]
        == "generated"
    )


def test_legacy_background_and_first_impression_are_recognized_without_overwriting_edits(
    tmp_path,
):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    role.memory_init_state = {
        "seed_self_pending": True,
        "seed_background_value": "旧背景",
        "relationship_baseline_source": "seed:first_impression",
        "relationship_baseline_value": "旧的初始关系",
    }
    content = render_memory_section(
        "SELF.md", DOCUMENT_DEFAULTS["SELF.md"], "## 我的性格与形象", "旧背景"
    )
    content = render_memory_section(
        "SELF.md",
        content,
        "## 我们的关系",
        "来源: seed:first_impression\n\n旧的初始关系",
    )
    assert resolve_self_seed_state(role, content)["status"] == "pending"
    assert (
        resolve_self_seed_state(role, content + "用户补充的内容")["status"]
        == "user_edited"
    )


def test_unknown_legacy_content_is_protected(tmp_path):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    assert resolve_self_seed_state(role, "旧的自定义内容")["status"] == "user_edited"


def test_pending_fingerprint_detects_edits_but_ignores_line_ending_changes(tmp_path):
    role = RoleStore(tmp_path).create_role(name="Mira", system_prompt="mira")
    role.memory_init_state = {
        "self_seed": {"status": "pending", "fingerprint": self_fingerprint("a\nb\n")}
    }
    assert resolve_self_seed_state(role, "a\r\nb\r\n")["status"] == "pending"
    assert resolve_self_seed_state(role, "a\nb\nc")["status"] == "user_edited"
