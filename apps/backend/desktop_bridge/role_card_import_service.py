from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from core.roles import RoleAggregateService, RoleAssetCategory, RoleStore
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
        description = str(overrides.get("description") or "")
        profile = self._profile_with_overrides(preview, overrides.get("profile"))
        character = dict(profile.get("character") or {})
        requested_prompt = str(overrides.get("system_prompt") or "").strip()
        if requested_prompt:
            character["behavior_rules"] = requested_prompt
        profile["character"] = character
        system_prompt = str(character.get("behavior_rules") or "").strip()
        if not system_prompt:
            system_prompt = "请遵循角色资料进行自然对话。"

        temporary_files: list[Path] = []
        try:
            avatar_source: Path | None = None
            imported_assets: list[tuple[str, str | None, Path]] = []
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
                if asset.kind in {"avatar", "emotion", "background", "asset"}:
                    imported_assets.append((asset.kind, asset.name, temporary_path))

            aggregate = await self._role_service.create_role_async(
                name=name,
                description=description,
                system_prompt=system_prompt,
                profile=profile,
                avatar_source=avatar_source,
                illustration_sources=[path for _, _, path in imported_assets],
            )
            if imported_assets:
                aggregate = await self._apply_imported_asset_metadata(
                    aggregate.role.id,
                    aggregate.role.illustrations,
                    imported_assets,
                )
            return {"role": aggregate.role.to_dict()}
        finally:
            self._imports.pop(import_id, None)
            for temporary_path in temporary_files:
                temporary_path.unlink(missing_ok=True)

    async def _apply_imported_asset_metadata(
        self,
        role_id: str,
        illustration_paths: list[str],
        imported_assets: list[tuple[str, str | None, Path]],
    ) -> Any:
        category = RoleAssetCategory(
            id="imported-role-card",
            name="导入角色卡",
            allow_role_send=False,
        )
        bindings = {path: category.id for path in illustration_paths}
        background_path = next(
            (
                illustration_paths[index]
                for index, (kind, _name, _path) in enumerate(imported_assets)
                if kind == "background"
            ),
            None,
        )
        mood_bindings = {
            name.strip(): illustration_paths[index]
            for index, (kind, name, _path) in enumerate(imported_assets)
            if kind == "emotion" and name and name.strip()
        }
        current = self._role_service.repository.get_required(role_id)
        runtime_config = dict(current.runtime_config)
        if mood_bindings:
            existing_bindings = dict(runtime_config.get("mood_illustration_bindings") or {})
            existing_bindings.update(mood_bindings)
            runtime_config["mood_illustration_bindings"] = existing_bindings
            runtime_config["mood_catalog"] = list(existing_bindings)
            if "neutral" in mood_bindings:
                runtime_config["default_mood"] = "neutral"
        return await self._role_service.update_role_async(
            role_id,
            runtime_config=runtime_config,
            chat_background=background_path,
            asset_categories=[*current.asset_categories, category],
            asset_category_bindings=bindings,
        )

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

    @staticmethod
    def _profile_with_overrides(preview: Any, raw_overrides: Any) -> dict[str, Any]:
        profile = dict(preview.profile)
        if preview.provenance is not None:
            profile["import_provenance"] = preview.provenance.to_dict()
        overrides = raw_overrides if isinstance(raw_overrides, dict) else {}
        for section in ("character", "greetings", "knowledge_base"):
            value = overrides.get(section)
            if isinstance(value, dict):
                profile[section] = {**dict(profile.get(section) or {}), **value}
        return profile
