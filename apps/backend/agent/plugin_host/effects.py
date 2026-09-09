"""可回滚副作用登记：插件的每次注册都以 effect 形式记录，卸载时逆序处置。"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

Dispose = Callable[[], Awaitable[None] | None]


@dataclass
class Effect:
    """单条已登记副作用：label 用于诊断，dispose 负责撤销。"""

    label: str
    dispose: Dispose


class EffectScope:
    """一个插件作用域内的全部副作用；dispose_all 逆序清理并汇总错误。"""

    def __init__(self, owner: str) -> None:
        self._owner = owner
        self._effects: list[Effect] = []
        self._disposed = False

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def labels(self) -> list[str]:
        """Returns registration labels in registration order, for diagnostics."""
        return [effect.label for effect in self._effects]

    def add(self, label: str, dispose: Dispose) -> None:
        # 已处置的作用域拒绝新登记，避免泄漏无人清理的资源
        if self._disposed:
            raise RuntimeError(f"EffectScope({self._owner}) 已处置，拒绝登记: {label}")
        self._effects.append(Effect(label=label, dispose=dispose))

    async def dispose_all(self) -> list[Exception]:
        """逆序执行全部 dispose；单条失败不阻断其余清理，返回收集到的错误。"""
        errors: list[Exception] = []
        while self._effects:
            effect = self._effects.pop()
            try:
                result = effect.dispose()
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.warning(
                    "插件副作用清理失败 (%s / %s): %s", self._owner, effect.label, e
                )
                errors.append(e)
        self._disposed = True
        return errors
