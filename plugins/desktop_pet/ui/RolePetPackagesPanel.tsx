import { useCallback, useEffect, useState } from "react";
import { CheckCircleIcon, TrashIcon } from "@phosphor-icons/react";
import { UploadIcon } from "../../../apps/desktop/renderer/src/shared/icons";
import { cx } from "../../../apps/desktop/renderer/src/shared/styles";
import type { PluginRoleAssetsComponentProps } from "../../../apps/desktop/renderer/src/plugins/pluginUiModuleContract";
import { noPetPackages, readPetPackages, type PetPackages } from "./petPackages";

/**
 * Manages this plugin's packages inside the role asset library.
 *
 * Until #181-D this was `apps/desktop/renderer/src/roles/RolePetPackagesPanel.tsx`,
 * rendered by name from `RoleAssetsPage` and fed from `RoleRecord.pet_packages`
 * — which is why the host's role model, its bridge and four props on that page
 * all had to know what a pet package is. It now contributes itself through the
 * `role.assets` slot and fetches its own rows over its own RPC namespace.
 *
 * TEMPORARY COUPLING: two `window.miraDesktop` calls remain, the same kind
 * `surface/petMenu.ts` documents and for the same missing piece —
 *
 * - `pickPetPackage()`: a native file dialog is main-process only, and no
 *   capability hands one to plugin UI yet.
 * - `syncPet()`: after a package is removed or selected the on-screen pet has
 *   to re-resolve, and this panel (main window) has no route to its own
 *   plugin's background code (plugin-host window). The host's `desktop:pet-sync`
 *   channel is the only bridge between them today.
 *
 * Both disappear with surface-to-background / plugin-to-plugin messaging (#218).
 */
export function RolePetPackagesPanel({ roleId, disabled, client, onRoleDataChanged }: PluginRoleAssetsComponentProps) {
  const [state, setState] = useState<PetPackages>(noPetPackages);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const parse = useCallback(
    (payload: unknown) => readPetPackages(payload, (path) => window.miraDesktop.localAssetUrl(path)),
    [],
  );

  // `disabled` is a dependency on purpose: it falls when the bridge comes up
  // or a host save finishes, and a list that failed during either needs a
  // second chance. Without it one transient refusal — `pets.list` is not
  // admission-exempt, so a channel-config reload answers `runtime_reloading` —
  // leaves the panel blank with a red line until the user navigates away.
  useEffect(() => {
    if (!roleId) {
      setState(noPetPackages);
      return;
    }
    let alive = true;
    void (async () => {
      try {
        const next = parse(await client.call<unknown>("pets.list", { role_id: roleId }));
        if (!alive) return;
        setState(next);
        setError("");
      } catch (reason) {
        if (!alive) return;
        // The previous rows are kept: a failed refresh is not evidence that the
        // packages are gone, and blanking the list would make a momentary
        // bridge hiccup look like data loss.
        setError(reason instanceof Error ? reason.message : String(reason));
      }
    })();
    return () => { alive = false; };
  }, [client, disabled, parse, roleId]);

  /** Runs one mutation, surfacing its failure instead of leaving the panel silent. */
  const run = useCallback(async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }, []);

  const onImport = useCallback(() => void run(async () => {
    const source = await window.miraDesktop.pickPetPackage();
    if (!source) return;
    setState(parse(await client.call<unknown>("pets.import", { role_id: roleId, source })));
    onRoleDataChanged();
  }), [client, onRoleDataChanged, parse, roleId, run]);

  const onRemove = useCallback((packageId: string) => void run(async () => {
    setState(parse(await client.call<unknown>("pets.remove", { role_id: roleId, package_id: packageId })));
    // Two different consumers, both required. `onRoleDataChanged` re-reads the
    // role the host still stores this on (the capability toggle reads
    // `selected_pet_package_id`, and the backend clears `desktop_pet_enabled`
    // when the selected package goes); `syncPet` tells the running pet to
    // re-resolve what it is rendering.
    onRoleDataChanged();
    await window.miraDesktop.syncPet();
  }), [client, onRoleDataChanged, parse, roleId, run]);

  const onSelect = useCallback((packageId: string) => void run(async () => {
    setState(parse(await client.call<unknown>("pets.select", { role_id: roleId, package_id: packageId })));
    onRoleDataChanged();
    await window.miraDesktop.syncPet();
  }), [client, onRoleDataChanged, parse, roleId, run]);

  // No role open: guessing one would let a click act on somebody else's packages.
  if (!roleId) return null;
  const locked = disabled || busy;

  return (
    <section className="border-t border-line-soft px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-medium text-ink">桌宠素材包</div>
        <button className="grid h-8 w-8 place-items-center rounded-md border border-line-soft bg-white text-ink-secondary transition hover:bg-surface-hover focus:outline-none" type="button" aria-label="导入桌宠素材包" title="导入桌宠素材包" disabled={locked} onClick={onImport}>
          <UploadIcon className="h-4 w-4 fill-current" />
        </button>
      </div>
      {error ? <div className="mb-2 text-xs text-danger-text">{error}</div> : null}
      <div className="grid grid-cols-2 gap-2">
        {state.packages.map((item) => (
          <div
            className={cx(
              "group relative overflow-hidden rounded-md border bg-white",
              state.selectedPackageId === item.id ? "border-accent shadow-soft" : "border-line-soft",
            )}
            key={item.id}
          >
            <button
              className="grid w-full gap-2 p-2 text-left transition hover:bg-surface-hover focus:outline-none"
              type="button"
              disabled={locked}
              aria-pressed={state.selectedPackageId === item.id}
              onClick={() => onSelect(item.id)}
            >
              <span className="relative block aspect-square w-full overflow-hidden bg-surface-soft">
                {item.previewUrl ? <img className="h-full w-full object-contain" src={item.previewUrl} alt={item.displayName} /> : null}
              </span>
              <span className="min-w-0 truncate text-xs text-ink">{item.displayName}</span>
            </button>
            <button
              className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-md border border-line-soft bg-white/92 text-ink-secondary opacity-0 shadow-soft transition hover:border-[var(--danger-300)] hover:bg-danger-soft hover:text-danger-text focus:opacity-100 group-hover:opacity-100 focus:outline-none"
              type="button"
              aria-label={`删除桌宠素材 ${item.displayName}`}
              disabled={locked}
              onClick={() => onRemove(item.id)}
            >
              <TrashIcon className="h-4 w-4" weight="bold" />
            </button>
            {state.selectedPackageId === item.id ? <CheckCircleIcon className="absolute left-2 top-2 h-5 w-5 text-ink-secondary" weight="fill" aria-label="已选中" /> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
