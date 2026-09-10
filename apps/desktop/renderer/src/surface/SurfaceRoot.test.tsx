import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { SurfaceRoot } from "./SurfaceRoot";
import {
  PluginSurfaceRegistry,
  type PluginSurfaceComponentProps,
  type SurfaceHandle,
} from "./pluginSurfaceRegistry";

/**
 * A function component is just a function and JSX compiles to a plain
 * `createElement` call, so invoking it and inspecting the returned element is
 * enough — no DOM needed. Same approach as `pluginUiModuleContract.test.ts`.
 */
const noopSurface: SurfaceHandle = {
  beginDrag() {},
  endDrag() {},
  setExtension() {},
  setClickThrough() {},
  onPlacement() { return () => {}; },
  onMessage() { return () => {}; },
  onState() { return () => {}; },
  ready() {},
  async showContextMenu() { return null; },
  activateMainWindow() {},
};

let errors: unknown[][] = [];
const realError = console.error;

beforeEach(() => {
  errors = [];
  console.error = (...args: unknown[]) => { errors.push(args); };
});

afterEach(() => { console.error = realError; });

/**
 * Invokes function components down to the first host element, so a test can
 * assert on what actually reaches the DOM rather than on the intermediate
 * component that produced it.
 */
function renderToHostElement(element: unknown): { type: unknown; props: Record<string, unknown> } {
  let current = element as { type: unknown; props: Record<string, unknown> };
  while (typeof current.type === "function") {
    current = (current.type as (props: unknown) => typeof current)(current.props);
  }
  return current;
}

function registryWith(pluginId: string, Component: (props: PluginSurfaceComponentProps) => null) {
  const registry = new PluginSurfaceRegistry();
  registry.register({ slot: "desktop.surface", pluginId, Component });
  return registry;
}

test("mounts the plugin named in the window URL, with its own scoped client", () => {
  const seen: PluginSurfaceComponentProps[] = [];
  const registry = registryWith("demo", (props) => { seen.push(props); return null; });

  const element = SurfaceRoot({
    search: "?plugin=demo&surface=main",
    surface: noopSurface,
    registry,
  }) as { type: unknown; props: PluginSurfaceComponentProps };

  assert.equal(typeof element.type, "function");
  // Invoke the element the root produced to observe the props it passed down.
  (element.type as (props: PluginSurfaceComponentProps) => null)(element.props);
  assert.equal(seen.length, 1);
  assert.equal(seen[0].surfaceId, "main");
  assert.equal(seen[0].surface, noopSurface);
  assert.equal(typeof seen[0].client.call, "function");
  assert.deepEqual(errors, []);
});

test("a window opened without its query string fails visibly instead of blank", () => {
  const registry = registryWith("demo", () => null);
  // A transparent always-on-top window rendering null is an invisible, unclickable
  // rectangle over the desktop — the failure has to be on screen, not just logged.
  const host = renderToHostElement(SurfaceRoot({ search: "", surface: noopSurface, registry }));
  assert.equal(host.type, "div");
  assert.equal(host.props.role, "alert");
  assert.equal(errors.length, 1);
});

test("a plugin with no registered surface fails visibly and names itself", () => {
  const registry = new PluginSurfaceRegistry();
  const host = renderToHostElement(SurfaceRoot({
    search: "?plugin=missing&surface=main",
    surface: noopSurface,
    registry,
  }));
  assert.equal(host.props.role, "alert");
  assert.equal(errors.length, 1);
  assert.match(String(errors[0][0]), /missing/);
});

test("one plugin's window never mounts another plugin's surface", () => {
  const registry = registryWith("demo", () => null);
  const host = renderToHostElement(SurfaceRoot({
    search: "?plugin=other&surface=main",
    surface: noopSurface,
    registry,
  }));
  assert.equal(host.props.role, "alert");
});
