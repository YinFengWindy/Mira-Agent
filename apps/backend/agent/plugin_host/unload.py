"""Public failure for plugins that require a process restart before replacement."""


class PluginRestartRequired(RuntimeError):
    """Rejects a hot transition before any affected plugin is disposed."""

    code = "plugin_restart_required"

    def __init__(self, plugin_ids: list[str]) -> None:
        self.plugin_ids = tuple(sorted(set(plugin_ids)))
        super().__init__(
            f"插件 {', '.join(self.plugin_ids)} 不支持热卸载；本次更改未保存；请退出应用后修改配置，再重新启动。"
        )

    def to_details(self) -> dict[str, object]:
        """Exposes affected identities through the shared runtime error envelope."""
        return {"plugin_ids": list(self.plugin_ids), "restart_required": True}
