import { Window } from "happy-dom";
import { act, type ReactNode } from "react";

/** Mounts a React component with DOM events and restores browser globals after cleanup. */
export async function mountTestComponent(component: ReactNode) {
  const browserWindow = new Window();
  const globals = {
    window: browserWindow,
    document: browserWindow.document,
    navigator: browserWindow.navigator,
    HTMLElement: browserWindow.HTMLElement,
    HTMLInputElement: browserWindow.HTMLInputElement,
    Event: browserWindow.Event,
    MouseEvent: browserWindow.MouseEvent,
    KeyboardEvent: browserWindow.KeyboardEvent,
    FocusEvent: browserWindow.FocusEvent,
    IS_REACT_ACT_ENVIRONMENT: true,
  };
  const originalGlobals = new Map<string, PropertyDescriptor | undefined>();
  for (const [name, value] of Object.entries(globals)) {
    originalGlobals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value });
  }
  const { createRoot } = await import("react-dom/client");
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  await act(async () => root.render(component));

  return {
    container,
    async render(next: ReactNode) {
      await act(async () => root.render(next));
    },
    async cleanup() {
      await act(async () => root.unmount());
      await browserWindow.happyDOM.close();
      for (const [name, descriptor] of originalGlobals) {
        if (descriptor) Object.defineProperty(globalThis, name, descriptor);
        else Reflect.deleteProperty(globalThis, name);
      }
    },
  };
}

/** Dispatches a native input event after bypassing React's programmatic value tracker. */
export async function changeInputValue(input: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
  if (!setValue) throw new Error("Input value setter is unavailable");
  await act(async () => {
    setValue.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
