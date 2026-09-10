import { createRoot } from "react-dom/client";
import { SurfaceRoot } from "./SurfaceRoot";
// Registers every plugin's `surface/index.tsx` before the root reads the
// registry. Imported for its side effect only.
import "./pluginSurfaceModules";

createRoot(document.getElementById("root") as HTMLElement).render(
  <SurfaceRoot search={window.location.search} surface={window.miraDesktop.surface} />,
);
