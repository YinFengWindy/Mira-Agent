import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { describePluginConfigFields } from "./jsonSchemaForm.js";

describe("describePluginConfigFields", () => {
  it("maps scalar types to dedicated field kinds and marks required fields", () => {
    const fields = describePluginConfigFields({
      type: "object",
      required: ["app_id"],
      properties: {
        app_id: { type: "string", title: "App ID" },
        max_retries: { type: "integer" },
        volume: { type: "number" },
        enabled: { type: "boolean" },
      },
    });

    assert.deepEqual(fields.map((f) => [f.key, f.kind, f.required]), [
      ["app_id", "string", true],
      ["max_retries", "integer", false],
      ["volume", "number", false],
      ["enabled", "boolean", false],
    ]);
    assert.equal(fields[0]?.label, "App ID");
  });

  it("flags secret-shaped string fields so they render masked", () => {
    const fields = describePluginConfigFields({
      properties: {
        client_secret: { type: "string" },
        access_token: { type: "string" },
        display_name: { type: "string" },
      },
    });

    assert.deepEqual(fields.map((f) => f.kind), ["secret", "secret", "string"]);
  });

  it("maps a string enum to an enum field with its options", () => {
    const fields = describePluginConfigFields({
      properties: { effort: { type: "string", enum: ["none", "low", "high"] } },
    });

    assert.equal(fields[0]?.kind, "enum");
    assert.deepEqual(fields[0]?.options, ["none", "low", "high"]);
  });

  it("unwraps an Optional[str]-shaped anyOf into its non-null member", () => {
    const fields = describePluginConfigFields({
      properties: {
        label: { anyOf: [{ type: "string" }, { type: "null" }], default: null },
      },
    });

    assert.equal(fields[0]?.kind, "string");
  });

  it("falls back to a raw json field for arrays, objects and unresolved refs", () => {
    const fields = describePluginConfigFields({
      properties: {
        groups: { type: "array", items: { $ref: "#/$defs/Group" } },
        nested: { $ref: "#/$defs/Nested" },
      },
    });

    assert.deepEqual(fields.map((f) => f.kind), ["json", "json"]);
  });
});
