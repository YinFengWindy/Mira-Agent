import { toFileUrl } from "../shared/format";
import type { RoleCardImportAsset } from "../shared/types";
import { duplicateEmotionAssets } from "./roleCardImportSelectors";

type RoleCardImportAssetsProps = {
  assets: RoleCardImportAsset[];
  selections: Record<string, string>;
  onSelectEmotion: (name: string, assetId: string) => void;
};

function assetLabel(kind: string | undefined) {
  if (kind === "avatar") return "头像";
  if (kind === "background") return "背景";
  if (kind === "emotion") return "心情";
  return "素材";
}

function AssetImage({ asset }: { asset: RoleCardImportAsset }) {
  return asset.preview_abs ? (
    <img className="h-20 w-20 rounded-md object-cover" src={toFileUrl(asset.preview_abs)} alt={`${assetLabel(asset.kind)}素材预览`} />
  ) : <div className="grid h-20 w-20 place-items-center rounded-md bg-[#F2F5F9] text-[11px] text-[#98A2B3]" aria-hidden="true">无预览</div>;
}

/** Shows imported images and explicit radio choices for duplicate emotions. */
export function RoleCardImportAssets({ assets, selections, onSelectEmotion }: RoleCardImportAssetsProps) {
  const duplicates = duplicateEmotionAssets(assets);
  const duplicateIds = new Set(duplicates.flatMap(([, group]) => group.map((asset) => asset.asset_id)));
  const ordinaryAssets = assets.filter((asset) => !duplicateIds.has(asset.asset_id));
  return (
    <div className="grid gap-4">
      {ordinaryAssets.length ? <div className="flex flex-wrap gap-3">
        {ordinaryAssets.map((asset) => (
          <figure className="m-0 grid w-20 justify-items-center gap-1.5" key={asset.asset_id}>
            <AssetImage asset={asset} />
            <figcaption className="w-full break-words text-center text-[11px] leading-4 text-[#667085]">{assetLabel(asset.kind)}{asset.name ? ` · ${asset.name}` : ""}</figcaption>
          </figure>
        ))}
      </div> : null}
      {duplicates.map(([name, group]) => (
        <fieldset className="min-w-0 border-0 p-0" key={name}>
          <legend className="mb-2 text-xs font-medium text-[#475467]">心情 · {name}</legend>
          <div className="flex flex-wrap gap-3">
            {group.map((asset, index) => (
              <label className="grid w-20 cursor-pointer justify-items-center gap-2" key={asset.asset_id} title={asset.path}>
                <AssetImage asset={asset} />
                <span className="flex items-center gap-1 text-xs text-[#667085]">
                  <input type="radio" name={`emotion-${name}`} value={asset.asset_id} checked={selections[name] === asset.asset_id} onChange={() => onSelectEmotion(name, asset.asset_id)} aria-label={`${name} 素材 ${index + 1}`} />
                  {index + 1}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
