/** Everything that decides whether the push-to-talk hotkey may accept new input. */
export type VoiceAvailabilityInputs = {
  voiceEnabled: boolean;
  petRunning: boolean;
  petVisible: boolean;
};

/** Side effects the main process applies once availability is resolved. */
export type VoiceAvailabilityEffects = {
  start(): void;
  stop(): void;
  stopAfterCurrentPress(): void;
  cancelCurrentTurn(): void;
};

/**
 * Voice input rides on the desktop pet: it is only reachable while the pet is
 * both running and visible, so a hidden pet must never leave the hotkey armed.
 */
export function isVoiceHotkeyAvailable({
  voiceEnabled,
  petRunning,
  petVisible,
}: VoiceAvailabilityInputs): boolean {
  return voiceEnabled && petRunning && petVisible;
}

/**
 * Applies the availability decision.
 *
 * `cancelCurrentTurn` separates the two reasons availability drops: the pet
 * going away must abort whatever is in flight, while a settings change only
 * stops admitting new presses and lets the current one finish.
 */
export function applyVoiceAvailability(
  available: boolean,
  cancelCurrentTurn: boolean,
  effects: VoiceAvailabilityEffects,
): void {
  if (available) {
    effects.start();
    return;
  }
  if (cancelCurrentTurn) {
    effects.stop();
    effects.cancelCurrentTurn();
    return;
  }
  effects.stopAfterCurrentPress();
}
