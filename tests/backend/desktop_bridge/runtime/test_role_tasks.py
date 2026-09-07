from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bootstrap.runtime.generations import RuntimeCandidate
from core.common.runtime_scope import current_runtime_lease
from core.roles.store import RoleStore
from desktop_bridge.runtime.role_tasks import RuntimeRoleTasks


@pytest.mark.asyncio
async def test_old_generation_job_remains_visible_and_cancels_through_its_owner(tmp_path):
    roles = RoleStore(tmp_path)
    role = roles.create_role(name="role", system_prompt="prompt")
    jobs = [{"job_id": "old-job", "origin_chat_id": f"role:{role.id}", "label": "old task",
             "task": "work", "started_at": "now"}]

    async def cancel(job_id):
        assert job_id == "old-job"
        assert current_runtime_lease().generation == 1
        jobs.clear()
        return True

    manager = SimpleNamespace(list_running_jobs=lambda: list(jobs), cancel=cancel)
    core = SimpleNamespace(tools=SimpleNamespace(get_tool=lambda name: SimpleNamespace(manager=manager)),
                           scheduler=None, memory_optimizer=None, stop=AsyncMock(),
                           memory_runtime=SimpleNamespace(aclose=AsyncMock()))
    old = RuntimeCandidate(1, core, SimpleNamespace(), published=True)
    job_lease = old.acquire()
    old.retired = True
    current = RuntimeCandidate(2, SimpleNamespace(tools=SimpleNamespace(get_tool=lambda name: None),
                                                  scheduler=None, memory_optimizer=None), SimpleNamespace())
    tasks = RuntimeRoleTasks(SimpleNamespace(retained_generations=(old, current)), roles)
    assert tasks.list_tasks(role.id)[0]["id"] == "old-job"
    assert await tasks.cancel_task(role.id, "old-job") == []
    await job_lease.release()
