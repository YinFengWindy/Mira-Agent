import { execFileSync } from "node:child_process";
import { resolveReleaseVersion } from "./release-version.mjs";

/** Reads the nearest release tag reachable from HEAD; untagged history keeps the package version. */
export function resolveDevVersion(repositoryRoot) {
  const revision = execFileSync("git", [
    "describe", "--tags", "--match", "v[0-9]*", "--abbrev=0", "--always",
  ], { cwd: repositoryRoot, encoding: "utf8", windowsHide: true }).trim();
  // With no reachable release tag, --always returns the commit hash.
  if (!revision.startsWith("v")) return undefined;
  return resolveReleaseVersion(revision.slice(1));
}
