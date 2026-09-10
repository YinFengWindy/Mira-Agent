import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig } from "vite";
import { resolve as resolvePath } from "node:path";
import react from "@vitejs/plugin-react";

const here = dirname(fileURLToPath(import.meta.url));
const desktopRoot = resolve(here, "..");
const repositoryRoot = resolve(desktopRoot, "..", "..");

export default defineConfig({
  root: here,
  base: "./",
  plugins: [react()],
  server: {
    fs: {
      // Plugin UI is compiled in from the top-level plugins/<id>/ui/ tree
      // (see issue #174), which sits outside this Vite root (renderer/);
      // without this, dev-server requests for those files are refused.
      allow: [repositoryRoot],
    },
  },
  build: {
    outDir: resolve(desktopRoot, "renderer-dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolvePath(here, "index.html"),
        pet: resolvePath(here, "pet.html"),
        // One host-owned entry for every plugin-owned desktop window. Adding a
        // per-plugin entry here is exactly the build-time coupling #181
        // removes — `pet.html` above is the last one, and goes away when the
        // pet moves onto this capability.
        surface: resolvePath(here, "surface.html"),
        voice: resolvePath(here, "voice.html"),
      },
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/@phosphor-icons/")) return "icons-vendor";
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/scheduler/")) return "react-vendor";
          if (id.includes("node_modules/motion/") || id.includes("node_modules/gsap/")) return "motion-vendor";
          return undefined;
        },
      },
    },
  },
});
