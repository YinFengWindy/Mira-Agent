/**
 * Pure JSON Schema -> form-field mapping used by the plugin config auto
 * form. Kept framework-free (no React, no DOM) so it is fully covered by
 * plain node:test unit tests; `PluginSchemaSettingsSection.tsx` only wires
 * these descriptors to input controls.
 *
 * Scope: a plugin's config model is a flat pydantic object in practice
 * (see `agent.plugin_host.config_schema`). Scalar properties (string,
 * number, integer, boolean, string enum) get a dedicated control; anything
 * this module cannot render safely as a scalar (nested objects, arrays,
 * unresolved `$ref`) falls back to a raw JSON field, which still reads and
 * writes correctly because the backend re-validates the whole submission.
 */

/**
 * A JSON Schema fragment, permissive enough to cover pydantic's exports.
 * Only lists the fields this module actually reads: a raw JSON Schema may
 * carry `items`/`$ref`/`$defs`/`default` too, but nothing here inspects
 * them (an unresolved `$ref`/array/object property already falls back to
 * the raw JSON field kind without needing to resolve it further).
 */
export type JsonSchema = {
  type?: string | string[];
  properties?: Record<string, JsonSchema>;
  required?: string[];
  enum?: unknown[];
  title?: string;
  description?: string;
  anyOf?: JsonSchema[];
};

export type PluginConfigFieldKind = "string" | "secret" | "number" | "integer" | "boolean" | "enum" | "json";

export type PluginConfigField = {
  key: string;
  kind: PluginConfigFieldKind;
  label: string;
  hint?: string;
  required: boolean;
  /** Only present for kind "enum". */
  options?: string[];
};

const SECRET_NAME_HINTS = ["secret", "token", "password"];

/** Heuristically flags a string field as sensitive so it renders masked. */
function looksLikeSecret(key: string) {
  const lowered = key.toLowerCase();
  return SECRET_NAME_HINTS.some((hint) => lowered.includes(hint));
}

/** Resolves the effective type/enum for a property, unwrapping a simple `anyOf` (Optional[X]). */
function resolveEffective(property: JsonSchema) {
  if (property.type || property.enum) return property;
  if (Array.isArray(property.anyOf)) {
    const candidate = property.anyOf.find((item) => item.type && item.type !== "null");
    if (candidate) return { ...property, type: candidate.type, enum: candidate.enum ?? property.enum };
  }
  return property;
}

function fieldKind(key: string, property: JsonSchema) {
  const effective = resolveEffective(property);
  if (Array.isArray(effective.enum) && effective.enum.every((item) => typeof item === "string")) return "enum";
  const type = Array.isArray(effective.type) ? effective.type[0] : effective.type;
  switch (type) {
    case "string":
      return looksLikeSecret(key) ? "secret" : "string";
    case "integer":
      return "integer";
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    default:
      // array, object, unresolved $ref, or an unrecognized/absent type.
      return "json";
  }
}

/** Converts a plugin's config JSON Schema into an ordered list of form fields. */
export function describePluginConfigFields(schema: JsonSchema): PluginConfigField[] {
  const properties = schema.properties ?? {};
  const required = new Set(schema.required ?? []);
  return Object.entries(properties).map(([key, property]) => {
    const effective = resolveEffective(property);
    const kind = fieldKind(key, property);
    const field: PluginConfigField = {
      key,
      kind,
      label: property.title ?? key,
      hint: property.description,
      required: required.has(key),
    };
    if (kind === "enum" && Array.isArray(effective.enum)) {
      field.options = effective.enum.filter((item): item is string => typeof item === "string");
    }
    return field;
  });
}
