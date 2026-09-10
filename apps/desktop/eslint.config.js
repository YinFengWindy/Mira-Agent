import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

/**
 * Builds the desktop lint configuration for a given set of file globs.
 *
 * Exported as a factory because the same rules have to cover two different
 * base directories. ESLint decides what is lintable from the *working
 * directory*, not from the config file's location, so plugin UI under the
 * top-level `plugins/` tree (compiled into the renderer bundle, see #174/#181)
 * can only be linted by an ESLint run rooted at the repository. The repo-root
 * `eslint.config.js` calls this with repo-relative globs; the default export
 * below keeps `pnpm --filter shiori-desktop run lint` working on its own with
 * package-relative ones.
 */
export function desktopEslintConfig(files) {
  return tseslint.config(
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
      files,
      languageOptions: {
        ecmaVersion: 2021,
        globals: {
          ...globals.browser,
          ...globals.node,
        },
      },
      plugins: {
        "react-hooks": reactHooks,
        "react-refresh": reactRefresh,
      },
      rules: {
        ...reactHooks.configs.recommended.rules,
        "react-refresh/only-export-components": "off",
        "react-hooks/set-state-in-effect": "off",
        "@typescript-eslint/triple-slash-reference": "off",
        "@typescript-eslint/no-explicit-any": "error",
      },
    },
  );
}

export default desktopEslintConfig([
  "src/**/*.ts",
  "src/**/*.tsx",
  "renderer/src/**/*.ts",
  "renderer/src/**/*.tsx",
]);
