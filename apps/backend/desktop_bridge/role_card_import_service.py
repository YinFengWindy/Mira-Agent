from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from core.roles import RoleAggregateService, RoleStore
from core.roles.card_import import RoleCardImportService


class DesktopRoleCardImportService:
    """Owns the desktop role-card staging, preview, and commit workflow."""

    def __init__(
        self,
        *,
        workspace: Path,
        role_service: RoleAggregateService,
        role_store: RoleStore,
    ) -> None:
        self._workspace = workspace.resolve()
        self._role_service = role_service
        self._role_store = role_store
        self._parser = RoleCardImportService()
        self._staging_root = (
            self._workspace / "private_runtime" / "imports" / "role-cards"
        ).resolve()
        self._staging_root.mkdir(parents=True, exist_ok=True)
        self._imports: dict[str, Path] = {}

    async def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = self._validate_source(payload.get("source"))
        preview = self._parser.preview(source)
        import_id = uuid.uuid4().hex
        self._imports[import_id] = source
        result = preview.to_dict()
        result.update(
            {
                "import_id": import_id,
                "system_prompt": str(
                    preview.profile.get("character", {}).get("behavior_rules") or ""
                ),
            }
        )
        return result

    async def commit(self, payload: dict[str, Any]) -> dict[str, Any]:
        import_id = str(payload.get("import_id") or "").strip()
        source = self._imports.get(import_id)
        if source is None:
            raise ValueError("角色卡导入预览已失效，请重新选择文件")
        preview = self._parser.preview(source)
        overrides = payload.get("overrides")
        overrides = overrides if isinstance(overrides, dict) else {}
        name = str(overrides.get("name") or preview.name).strip()
        description = str(overrides.get("description") or preview.description)
        profile = dict(preview.profile)
        character = dict(profile.get("character") or {})
        requested_prompt = str(overrides.get("system_prompt") or "").strip()
        if requested_prompt:
            character["behavior_rules"] = requested_prompt
        profile["character"] = character
        system_prompt = str(character.get("behavior_rules") or "").strip()
        if not system_prompt:
            system_prompt = str(character.get("profile") or "").strip()
        if not system_prompt:
            system_prompt = "请遵循角色资料进行自然对话。"

        temporary_files: list[Path] = []
        try:
            avatar_source: Path | None = None
            illustrations: list[Path] = []
            for index, asset in enumerate(preview.assets):
                if asset.data is None:
                    continue
                suffix = Path(asset.path).suffix or ".png"
                handle = tempfile.NamedTemporaryFile(
                    prefix=f"shiori-role-card-{index}-",
                    suffix=suffix,
                    dir=self._staging_root,
                    delete=False,
                )
                temporary_path = Path(handle.name)
                handle.write(asset.data)
                handle.close()
                temporary_files.append(temporary_path)
                if asset.kind == "avatar" and avatar_source is None:
                    avatar_source = temporary_path
                elif asset.kind in {"emotion", "background", "asset"}:
                    illustrations.append(temporary_path)

            aggregate = await self._role_service.create_role_async(
                name=name,
                description=description,
                system_prompt=system_prompt,
                profile=profile,
                avatar_source=avatar_source,
                illustration_sources=illustrations,
            )
            return {"role": aggregate.role.to_dict()}
        finally:
            self._imports.pop(import_id, None)
            for temporary_path in temporary_files:
                temporary_path.unlink(missing_ok=True)

    async def cancel(self, payload: dict[str, Any]) -> dict[str, Any]:
        import_id = str(payload.get("import_id") or "").strip()
        self._imports.pop(import_id, None)
        return {"cancelled": bool(import_id)}

    def _validate_source(self, raw_source: Any) -> Path:
        source = Path(str(raw_source or "")).expanduser().resolve()
        try:
            source.relative_to(self._staging_root)
        except ValueError as error:
            raise ValueError("角色卡文件必须来自受控导入目录") from error
        if not source.is_file():
            raise FileNotFoundError(f"角色卡不存在: {source.name}")
        if source.suffix.casefold() not in {".json", ".png", ".apng", ".charx"}:
            raise ValueError("不支持的角色卡格式")
        return source
