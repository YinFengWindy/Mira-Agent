import { useCallback, useEffect, useRef, useState } from "react";
import type { SettingsFormData, SettingsSnapshot } from "../shared/types";
import { cloneSettings, loadSettingsPageData, settingsEqual, shouldRetryFailedSettingsLoad } from "./settingsPersistence";
import type { SettingsDraftUpdater, SettingsSavePhase } from "./settingsPageTypes";
import { SettingsSaveQueue } from "./settingsSaveQueue";

type UseSettingsPageControllerArgs = { bridgeReady: boolean };

/** Assembles the settings snapshot, editable draft, and transaction queue. */
export function useSettingsPageController({ bridgeReady }: UseSettingsPageControllerArgs) {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot | null>(null);
  const [draft, setDraft] = useState<SettingsFormData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [savePhase, setSavePhase] = useState<SettingsSavePhase>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const loadRequestIdRef = useRef(0);
  const [saveQueue] = useState(() => new SettingsSaveQueue({
    api: window.miraDesktop,
    onApplied: (nextSnapshot, submitted, nextDraft) => {
      setSnapshot(nextSnapshot);
      setDraft((current) => settingsEqual(current, submitted) ? nextDraft : current);
    },
    onStatus: (phase, message) => {
      setSavePhase(phase);
      setStatusMessage(message);
    },
  }));

  const loadPageData = useCallback(async () => {
    const requestId = ++loadRequestIdRef.current;
    try {
      const loaded = await loadSettingsPageData(window.miraDesktop);
      if (loadRequestIdRef.current !== requestId) return;
      saveQueue.reset(loaded.snapshot.generation);
      setSnapshot(loaded.snapshot);
      setDraft(cloneSettings(loaded.snapshot.formData));
      setLoadError("");
      setSavePhase("idle");
      setStatusMessage("");
    } catch (error) {
      if (loadRequestIdRef.current !== requestId) return;
      setLoadError(error instanceof Error ? error.message : String(error));
    }
  }, [saveQueue]);

  useEffect(() => { void loadPageData(); }, [loadPageData]);
  useEffect(() => {
    if (shouldRetryFailedSettingsLoad({ bridgeReady, loadError })) void loadPageData();
  }, [bridgeReady, loadError, loadPageData]);
  useEffect(() => () => { loadRequestIdRef.current += 1; }, []);
  useEffect(() => {
    if (snapshot && draft) saveQueue.enqueue(draft, snapshot.formData);
  }, [draft, snapshot, saveQueue]);

  const updateDraft: SettingsDraftUpdater = (mutator) => {
    setDraft((current) => {
      if (!current) return current;
      const next = mutator(cloneSettings(current));
      return settingsEqual(current, next) ? current : next;
    });
  };

  return {
    draft, loadError, savePhase, statusMessage, updateDraft,
    retrySave: () => saveQueue.retry(),
    reloadSettings: () => void loadPageData(),
  };
}
