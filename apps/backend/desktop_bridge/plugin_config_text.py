"""Table-scoped TOML editing for ``[plugins.<id>]``.

``plugin.config.set`` must rewrite exactly one plugin's table while leaving
the rest of the persisted config file byte-for-byte untouched (user comments,
ordering, unrelated tables). A full ``toml.dumps`` round-trip of the whole
document would lose comments and reorder tables, so this module locates the
existing ``[plugins.<id>]`` block (and any of its own sub-tables) by line
scanning and replaces only that span; when the table does not exist yet, it
appends a new one.
"""

from __future__ import annotations

import re
from typing import Any

import toml

# Matches a standalone table or array-of-tables header line, e.g. ``[a.b]``
# or ``[[a.b]]``; group 1 keeps the bracket run so the same width is reused
# when the dumped block's own headers are reparented under ``plugins.``.
_HEADER_RE = re.compile(r"^(\[{1,2})\s*([^\[\]]+?)\s*(\]{1,2})\s*$")


def merge_plugin_table(config_toml: str, plugin_id: str, values: dict[str, Any]) -> str:
    """Returns ``config_toml`` with ``[plugins.<plugin_id>]`` replaced by ``values``.

    Everything before the replaced table and everything from the next
    unrelated header onward is preserved exactly; only the target plugin's
    own table (including its sub-tables) is rewritten.
    """

    lines = config_toml.splitlines(keepends=True)
    prefix = f"plugins.{plugin_id}"
    start, end = _locate_table(lines, prefix)
    block = _render_table(plugin_id, values)
    if start is None:
        return _append_table(config_toml, block)
    return "".join(lines[:start] + [block] + lines[end:])


def _locate_table(lines: list[str], prefix: str) -> tuple[int | None, int]:
    """Returns the ``[start, end)`` line span owned by ``prefix``, if present."""

    start: int | None = None
    end = len(lines)
    for index, raw_line in enumerate(lines):
        match = _HEADER_RE.match(raw_line.strip())
        if not match:
            continue
        path = match.group(2)
        owned = path == prefix or path.startswith(prefix + ".")
        if start is None:
            if owned:
                start = index
            continue
        if not owned:
            end = index
            break
    return start, end


def _append_table(config_toml: str, block: str) -> str:
    if not config_toml.strip():
        return block
    separator = "" if config_toml.endswith("\n") else "\n"
    return f"{config_toml}{separator}\n{block}"


def _render_table(plugin_id: str, values: dict[str, Any]) -> str:
    """Dumps ``values`` as ``[plugins.<plugin_id>...]`` header(s) plus fields."""

    rendered = toml.dumps({plugin_id: values})
    out_lines: list[str] = []
    for line in rendered.splitlines():
        match = _HEADER_RE.match(line)
        if match:
            open_brackets, path, close_brackets = match.groups()
            out_lines.append(f"{open_brackets}plugins.{path}{close_brackets}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines).rstrip("\n") + "\n"
