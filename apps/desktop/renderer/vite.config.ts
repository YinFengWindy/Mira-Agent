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
        // One host-owned entry for every plugin-owned desktop window, told
        // which plugin to mount through its query string. Adding a per-plugin
        // entry here is exactly the build-time coupling #181 removed: the pet's
        // `pet.html` was the last one, and it is gone.
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
