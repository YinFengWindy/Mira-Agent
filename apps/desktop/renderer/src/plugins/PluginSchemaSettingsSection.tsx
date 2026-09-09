import { useEffect, useRef, useState } from "react";
import { SettingsField } from "../settings/SettingsField";
import {
  SettingsSecretInput,
  SettingsSectionCard,
  SettingsToggleField,
  settingsInputClass,
} from "../settings/SettingsFieldPrimitives";
import { SettingsSaveFeedback } from "../settings/SettingsSaveFeedback";
import { parseSettingsNumber } from "../settings/settingsSectionUtils";
import { cardClass, cx, ghostButtonClass, textareaClass } from "../shared/styles";
import { describePluginConfigFields, type PluginConfigField } from "./jsonSchemaForm";
import { usePluginConfigController } from "./usePluginConfigController";

type FieldRowProps = {
  field: PluginConfigField;
  value: unknown;
  onChange: (value: unknown) => void;
};

/** Renders one scalar control, or a raw JSON editor for shapes the form can't render natively. */
function FieldRow({ field, value, onChange }: FieldRowProps) {
  if (field.kind === "boolean") {
    return (
      <SettingsToggleField
        label={field.label}
        hint={field.hint}
        checked={Boolean(value)}
        onChange={onChange}
      />
    );
  }
  if (field.kind === "enum") {
    return (
      <SettingsField label={field.label} hint={field.hint}>
        <select
          className={settingsInputClass}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
        >
          {(field.options ?? []).map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </SettingsField>
    );
  }
  if (field.kind === "secret") {
    return (
      <SettingsField label={field.label} hint={field.hint}>
        <SettingsSecretInput value={String(value ?? "")} onChange={onChange} ariaLabel={field.label} />
      </SettingsField>
    );
  }
  if (field.kind === "number" || field.kind === "integer") {
    return (
      <SettingsField label={field.label} hint={field.hint}>
        <input
          className={settingsInputClass}
          value={String(value ?? 0)}
          onChange={(event) => onChange(parseSettingsNumber(event.target.value, Number(value ?? 0)))}
        />
      </SettingsField>
    );
  }
  if (field.kind === "json") {
    return <JsonFieldRow field={field} value={value} onChange={onChange} />;
  }
  return (
    <SettingsField label={field.label} hint={field.hint}>
      <input
        className={settingsInputClass}
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value)}
      />
    </SettingsField>
  );
}

/**
 * Raw JSON editor for fields whose shape (array/object/$ref) has no
 * dedicated control. Resyncs its text from `value` whenever that value
 * changed for a reason other than this field's own last edit (e.g.
 * `reloadConfig` replacing the whole draft) — otherwise a reload after this
 * field mounted would leave the textarea showing stale content.
 */
function JsonFieldRow({ field, value, onChange }: FieldRowProps) {
  const [text, setText] = useState(() => JSON.stringify(value ?? null, null, 2));
  const [invalid, setInvalid] = useState(false);
  const pendingLocalEditRef = useRef(false);

  useEffect(() => {
    if (pendingLocalEditRef.current) {
      pendingLocalEditRef.current = false;
      return;
    }
    setText(JSON.stringify(value ?? null, null, 2));
    setInvalid(false);
  }, [value]);

  return (
    <SettingsField label={field.label} hint={field.hint} layout="stack">
      <textarea
        className={cx(textareaClass, "font-mono text-body-sm", invalid && "border-danger")}
        value={text}
        onChange={(event) => {
          const nextText = event.target.value;
          setText(nextText);
          try {
            const parsed = JSON.parse(nextText);
            pendingLocalEditRef.current = true;
            onChange(parsed);
            setInvalid(false);
          } catch {
            setInvalid(true);
          }
        }}
      />
      {invalid ? <p className="mt-1 text-caption text-danger-text">JSON 格式无效</p> : null}
    </SettingsField>
  );
}

type PluginSchemaSettingsSectionProps = { pluginId: string };

/** Renders and autosaves a plugin's config form, generated from its declared JSON Schema. */
export function PluginSchemaSettingsSection({ pluginId }: PluginSchemaSettingsSectionProps) {
  const { schema, draft, loadError, savePhase, statusMessage, updateDraft, retrySave, reloadConfig } =
    usePluginConfigController(pluginId);

  if (loadError) {
    return (
      <div className={cx(cardClass, "p-6 text-sm leading-6 text-danger-text")}>
        插件配置加载失败：{loadError}
        <button type="button" className={cx(ghostButtonClass, "ml-3")} onClick={reloadConfig}>重新加载</button>
      </div>
    );
  }
  if (!schema || !draft) {
    return <div className="text-sm text-ink-muted">正在加载插件配置…</div>;
  }

  const fields = describePluginConfigFields(schema);
  return (
    <div className="grid gap-4">
      <SettingsSaveFeedback
        phase={savePhase}
        message={statusMessage}
        onRetry={retrySave}
        onReload={reloadConfig}
      />
      <SettingsSectionCard>
        {fields.map((field) => (
          <FieldRow
            key={field.key}
            field={field}
            value={draft[field.key]}
            onChange={(value) => updateDraft((current) => ({ ...current, [field.key]: value }))}
          />
        ))}
      </SettingsSectionCard>
    </div>
  );
}

/** Binds a plugin id into a settings.section-compatible component (registry entry shape). */
export function createPluginSchemaSettingsSection(pluginId: string) {
  return function BoundPluginSchemaSettingsSection() {
    return <PluginSchemaSettingsSection pluginId={pluginId} />;
  };
}
