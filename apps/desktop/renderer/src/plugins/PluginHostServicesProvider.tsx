import { createContext, useContext, type ReactNode } from "react";
import type { PluginHostServices } from "./pluginHostServices";

const HostServicesContext = createContext<PluginHostServices | null>(null);

/** Gives an entire plugin UI subtree access to the host's explicit service contract. */
export function PluginHostServicesProvider({ services, children }: { services: PluginHostServices; children: ReactNode }) {
  return <HostServicesContext.Provider value={services}>{children}</HostServicesContext.Provider>;
}

/** Requires the services injected when the host mounts a plugin contribution. */
export function usePluginHostServices() {
  const services = useContext(HostServicesContext);
  if (!services) throw new Error("插件 UI 缺少宿主服务");
  return services;
}
