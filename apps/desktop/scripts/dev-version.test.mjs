import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { resolveDevVersion } from "./dev-version.mjs";

function createRepository(t) {
  const directory = mkdtempSync(join(tmpdir(), "shiori-dev-version-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const git = (...args) => execFileSync("git", [
    "-c", "user.name=Version Test", "-c", "user.email=version@example.invalid",
    "-c", "commit.gpgSign=false", "-c", "tag.gpgSign=false", ...args,
  ], { cwd: directory, encoding: "utf8", windowsHide: true });
  git("init", "--initial-branch=main");
  git("commit", "--allow-empty", "-m", "Initial commit");
  return { directory, git };
}

test("dev version follows new release tags and commits after the release", (t) => {
  const { directory, git } = createRepository(t);
  git("tag", "v0.1.0");
  assert.equal(resolveDevVersion(directory), "0.1.0");
  git("commit", "--allow-empty", "-m", "Next release");
  git("tag", "v0.2.0");
  assert.equal(resolveDevVersion(directory), "0.2.0");
  git("commit", "--allow-empty", "-m", "Development");
  git("tag", "unrelated-tag");
  assert.equal(resolveDevVersion(directory), "0.2.0");
});

test("dev version ignores release tags outside the current history", (t) => {
  const { directory, git } = createRepository(t);
  git("tag", "v0.1.0");
  git("branch", "older-development");
  git("commit", "--allow-empty", "-m", "Next release");
  git("tag", "v0.2.0");
  git("checkout", "older-development");
  assert.equal(resolveDevVersion(directory), "0.1.0");
});

test("dev version leaves untagged history on the package version", (t) => {
  const { directory, git } = createRepository(t);
  git("tag", "unrelated-tag");
  assert.equal(resolveDevVersion(directory), undefined);
});

test("dev version shares release validation including prerelease tags", (t) => {
  const { directory, git } = createRepository(t);
  git("tag", "-a", "v0.3.0-beta.1", "-m", "Prerelease");
  assert.equal(resolveDevVersion(directory), "0.3.0-beta.1");
  git("commit", "--allow-empty", "-m", "Invalid release");
  git("tag", "v0.invalid");
  assert.throws(() => resolveDevVersion(directory), /Invalid release version/);
});
