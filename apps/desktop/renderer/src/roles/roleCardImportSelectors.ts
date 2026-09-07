import type { RoleCardImportAsset } from "../shared/types";

/** Groups decoded, named emotion images that require an explicit choice. */
export function duplicateEmotionAssets(assets: RoleCardImportAsset[]) {
  const groups = new Map<string, RoleCardImportAsset[]>();
  for (const asset of assets) {
    if (asset.kind !== "emotion" || !asset.name || asset.size === undefined) continue;
    const group = groups.get(asset.name) ?? [];
    group.push(asset);
    groups.set(asset.name, group);
  }
  return [...groups.entries()].filter(([, group]) => group.length > 1);
}

/** Reports unresolved or stale choices before a card import is submitted. */
export function hasUnselectedEmotions(assets: RoleCardImportAsset[], selections: Record<string, string>) {
  return duplicateEmotionAssets(assets).some(([name, group]) => !group.some((asset) => asset.asset_id === selections[name]));
}
