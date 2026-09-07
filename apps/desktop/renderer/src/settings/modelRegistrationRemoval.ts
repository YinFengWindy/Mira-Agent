import type { ModelRegistrationFormData, PendingRoleModelUpdate } from "../../../src/bridge/shared";
import type { RoleRecord } from "../shared/types";

/** Confirms removal and stages unbinding without implicitly selecting another model. */
export async function prepareModelRegistrationRemoval(
  registration: ModelRegistrationFormData,
  pendingUpdates: PendingRoleModelUpdate[] = [],
): Promise<PendingRoleModelUpdate[] | null> {
  const response = await window.miraDesktop.invoke({ method: "roles.list", payload: {} });
  if (response.error) {
    window.alert(response.error.message);
    return null;
  }
  const roles = Array.isArray(response.payload.roles) ? response.payload.roles as RoleRecord[] : [];
  const effectiveRoles = roles.map((role) => ({
    ...role,
    runtime_config: {
      ...role.runtime_config,
      ...pendingUpdates.find((update) => update.roleId === role.id)?.runtimeConfig,
    },
  }));
  const affectedRoles = effectiveRoles.filter((role) => (
    role.runtime_config.dialogue_model_registration_id === registration.id
    || role.runtime_config.visual_model_registration_id === registration.id
  ));
  const impact = affectedRoles.length > 0
    ? `\n受影响角色：${affectedRoles.map((role) => role.name).join("、")}`
    : "";
  if (!window.confirm(`删除模型注册“${registration.model}”？${impact}`)) return null;

  return affectedRoles.map((role) => ({
    roleId: role.id,
    runtimeConfig: {
      dialogue_model_registration_id: role.runtime_config.dialogue_model_registration_id === registration.id
        ? ""
        : role.runtime_config.dialogue_model_registration_id,
      visual_model_registration_id: role.runtime_config.visual_model_registration_id === registration.id
        ? ""
        : role.runtime_config.visual_model_registration_id,
    },
  }));
}
