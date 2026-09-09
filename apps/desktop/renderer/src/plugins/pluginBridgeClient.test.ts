import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createPluginRpcClient } from "./pluginBridgeClient.js";

describe("createPluginRpcClient", () => {
  it("prefixes every call with the owning plugin's own plugin.<id>.* namespace", async () => {
    const calls: string[] = [];
    const invoke = async ({ method, payload }: { method: string; payload: Record<string, unknown> }) => {
      calls.push(method);
      return { id: "1", type: "response" as const, method, error: null, payload: { echoed: payload } };
    };

    const client = createPluginRpcClient("demo", invoke);
    await client.call("doThing", { x: 1 });
    await client.call("other");

    // The plugin only ever supplies the bare method name; the client — not
    // the caller — owns constructing the full "plugin.<id>.<method>" name,
    // so there is no way for injected client code to address another
    // plugin's namespace or a bare top-level bridge method.
    assert.deepEqual(calls, ["plugin.demo.doThing", "plugin.demo.other"]);
  });

  it("does not touch window.miraDesktop until a call is actually made", () => {
    // Building the client (as pluginUiModuleContract.tsx does once per
    // plugin at UI registration time) must not require window.miraDesktop
    // to exist yet; only invoking .call() should reach it.
    assert.doesNotThrow(() => createPluginRpcClient("demo"));
  });
});
