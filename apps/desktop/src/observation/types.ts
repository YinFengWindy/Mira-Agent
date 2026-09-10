/** Lifecycle states that determine the pet's observation presentation. */
export type ObservationStatus = "off" | "observing" | "reviewing" | "paused" | "failed";

/** Main-process payload for the pet renderer's status and optional reply bubble. */
export type PetObservationPayload = {
  status: ObservationStatus;
  enabled: boolean;
  bubble: string;
  persistent: boolean;
};

// `PetBubbleLayout` used to live here: the main process measured the reply
// bubble and told the pet renderer which side to draw it on. Since #181-B the
// pet decides that itself from the work area the host reports, and asks for a
// surface extension — see `plugins/desktop_pet/surface/bubbleExtension.ts`.
