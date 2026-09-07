"""One declarative policy record per bridge method.

Both request scheduling (`request_dispatcher`) and endpoint routing
(`desktop_bridge.runtime.service`) read this table, so adding a method
means declaring its concurrency lane, reload admission and cancellation
ownership in exactly one place. Unregistered methods keep the historical
conservative defaults: serial mutation lane, subject to reload admission,
served by the current generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Concurrency(Enum):
    """Which dispatcher lane runs the request."""

    READ_ONLY = "read_only"
    INTEGRATION = "integration"
    MUTATION = "mutation"
    # The settings transaction owns its serial lock; scheduling it through a
    # shared lane would starve health checks and cancellation while it drains.
    SETTINGS_APPLY = "settings_apply"


class Handler(Enum):
    """Which endpoint branch of ReloadableDesktopService serves the request."""

    GENERATION = "generation"
    SETTINGS = "settings"
    ROLE_TASKS = "role_tasks"


class OwnerRouting(Enum):
    """How the endpoint picks the runtime generation that serves the request."""

    CURRENT = "current"
    BUSY_CHAT_SESSION = "busy_chat_session"
    BUSY_VOICE_TURN = "busy_voice_turn"
    BUSY_VOICE_SYNTHESIS = "busy_voice_synthesis"


@dataclass(frozen=True)
class MethodPolicy:
    concurrency: Concurrency = Concurrency.MUTATION
    admission_exempt: bool = False
    owner_routing: OwnerRouting = OwnerRouting.CURRENT
    handler: Handler = Handler.GENERATION


_DEFAULT_POLICY = MethodPolicy()

METHOD_POLICIES: dict[str, MethodPolicy] = {
    "health": MethodPolicy(concurrency=Concurrency.READ_ONLY, admission_exempt=True),
    "runtime.status": MethodPolicy(
        concurrency=Concurrency.READ_ONLY, admission_exempt=True, handler=Handler.SETTINGS,
    ),
    "runtime.apply": MethodPolicy(
        concurrency=Concurrency.SETTINGS_APPLY, admission_exempt=True, handler=Handler.SETTINGS,
    ),
    "roles.tasks.list": MethodPolicy(
        concurrency=Concurrency.READ_ONLY, admission_exempt=True, handler=Handler.ROLE_TASKS,
    ),
    "roles.tasks.cancel": MethodPolicy(admission_exempt=True, handler=Handler.ROLE_TASKS),
    "roles.list": MethodPolicy(concurrency=Concurrency.READ_ONLY, admission_exempt=True),
    "session.messagesPage": MethodPolicy(concurrency=Concurrency.READ_ONLY, admission_exempt=True),
    "session.messagesAround": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "session.search": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "session.imageHistory": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "novelai.history": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "novelai.prompt_tags.list": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "stories.list": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "stories.get": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "stories.cg.list": MethodPolicy(concurrency=Concurrency.READ_ONLY),
    "novelai.generate": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "novelai.regenerateMessageMedia": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "stories.create": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "stories.input": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "stories.continue": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "stories.cg.retry": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "stories.cg.regenerate": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "observation.analyze": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "voice.synthesize": MethodPolicy(concurrency=Concurrency.INTEGRATION),
    "voice.synthesize.cancel": MethodPolicy(
        concurrency=Concurrency.INTEGRATION,
        admission_exempt=True,
        owner_routing=OwnerRouting.BUSY_VOICE_SYNTHESIS,
    ),
    "chat.cancel": MethodPolicy(
        admission_exempt=True, owner_routing=OwnerRouting.BUSY_CHAT_SESSION,
    ),
    "voice.turn.cancel": MethodPolicy(
        admission_exempt=True, owner_routing=OwnerRouting.BUSY_VOICE_TURN,
    ),
}


def method_policy(method: str) -> MethodPolicy:
    """Returns the declared policy, or the conservative default for new methods."""
    return METHOD_POLICIES.get(method, _DEFAULT_POLICY)
