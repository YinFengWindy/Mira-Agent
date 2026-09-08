/** Local, versioned progress; actual registrations and roles determine remaining steps. */
export type OnboardingProgress = {
  version: number;
  step: "model" | "role" | "workspace";
  completed: boolean;
  completedVersions: number[];
};

/** Storage keys deliberately exclude credentials and role drafts. */
export const onboardingStorageKey = "onboarding.v1";
/** Only the current Electron process may honor a temporary dismissal. */
export const onboardingSkipKey = "onboarding.skippedSession";
/** Increase when shipping a new tutorial, retaining prior completion history. */
export const onboardingVersion = 1;

/** Reads persisted progress with an explicit schema check. */
export function readOnboardingProgress(storage: Pick<Storage, "getItem">): OnboardingProgress | null {
  const raw = storage.getItem(onboardingStorageKey);
  if (!raw) return null;
  const value: unknown = JSON.parse(raw);
  if (!value || typeof value !== "object" || !("version" in value) || typeof value.version !== "number"
    || !("step" in value) || !["model", "role", "workspace"].includes(String(value.step))
    || !("completed" in value) || typeof value.completed !== "boolean"
    || !("completedVersions" in value) || !Array.isArray(value.completedVersions)
    || !value.completedVersions.every((version) => Number.isInteger(version) && version > 0)) {
    throw new Error("新手引导状态无效。");
  }
  return value as OnboardingProgress;
}

/** Reconciles tutorial history with successfully loaded application data. */
export function reconcileOnboarding(progress: OnboardingProgress | null, hasModel: boolean, hasRole: boolean, version = onboardingVersion): OnboardingProgress {
  const completedVersions = progress?.completedVersions ?? [];
  // Existing installations are exempt; an enrolled user always resumes unfinished work.
  const completed = completedVersions.includes(version)
    || Boolean(progress?.version === version && progress.completed)
    || (!progress && (hasModel || hasRole));
  return {
    version,
    step: hasModel ? (hasRole ? "workspace" : "role") : "model",
    completed,
    completedVersions: completed && !completedVersions.includes(version) ? [...completedVersions, version] : completedVersions,
  };
}

/** Marks only the current tutorial complete after workspace entry succeeds. */
export function completeOnboarding(progress: OnboardingProgress): OnboardingProgress {
  return { ...progress, completed: true, completedVersions: [...new Set([...progress.completedVersions, progress.version])] };
}
