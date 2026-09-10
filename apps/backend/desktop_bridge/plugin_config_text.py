"""Table-scoped TOML editing for ``[plugins.<id>]``.

``plugin.config.set`` must rewrite exactly one plugin's table while leaving
the rest of the persisted config file untouched (ordering, unrelated tables,
most surrounding comments). A full ``toml.dumps`` round-trip of the whole
document would lose comments and reorder tables, so this module locates the
existing ``[plugins.<id>]`` block (and any of its own sub-tables) by line
scanning and replaces only that span; when the table does not exist yet, it
appends a new one.

The scan is statement-aware, not a naive per-line regex match: it tracks
bracket depth and multi-line (triple-quoted) string state across lines so a
multi-line array's own last element (e.g. a lone ``[3]`` line) or a header-
shaped substring inside a multi-line string is never mistaken for a real
table header. Header lines are also matched with any trailing ``# comment``
stripped first, and header paths are parsed key-by-key (quoted segments
included) so a quoted or dotted plugin id is matched correctly instead of by
raw substring comparison.

Known limitation: comment/blank lines sitting directly between the target
table's last line and the next table's header are treated as part of the
replaced span (there is no reliable way to tell whether they describe the
plugin's own trailing state or the next table), so they are dropped rather
than preserved byte-for-byte. Everything before the target table and
everything from the next table's header onward is preserved exactly.
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
    prefix_segments = ["plugins", plugin_id]
    spans = _locate_owned_spans(lines, prefix_segments)
    block = _render_table(plugin_id, values)
    if not spans:
        return _append_table(config_toml, block)
    # 新表整体写在第一段的位置，其余归属本插件的表段（可能被无关表隔开）一并移除；
    # 只处理第一段会把后面的旧子表留下，生成重复表声明，整份文档随即无法解析。
    out: list[str] = list(lines[: spans[0][0]])
    out.append(block)
    previous_end = spans[0][1]
    for start, end in spans[1:]:
        out.extend(lines[previous_end:start])
        previous_end = end
    out.extend(lines[previous_end:])
    return "".join(out)


def _locate_owned_spans(
    lines: list[str], prefix_segments: list[str]
) -> list[tuple[int, int]]:
    """Returns every ``[start, end)`` line span whose table is owned by the prefix.

    A plugin's main table and its sub-tables are usually contiguous, but nothing
    in TOML requires that — an unrelated table may sit between them, and both
    orderings parse identically. Collecting every owned span (merging adjacent
    ones) is therefore the only correct basis for replacement.

    Only lines that begin a new top-level TOML statement (depth 0, not inside
    a multi-line string) are considered as header candidates; continuation
    lines of a multi-line array or string can never be one, no matter what
    their stripped text looks like.
    """

    headers: list[tuple[int, bool]] = []
    depth = 0
    in_multiline_basic = False
    in_multiline_literal = False
    for index, raw_line in enumerate(lines):
        is_statement_start = depth == 0 and not in_multiline_basic and not in_multiline_literal
        depth, in_multiline_basic, in_multiline_literal, comment_start = _scan_line(
            raw_line, depth, in_multiline_basic, in_multiline_literal,
        )
        if not is_statement_start:
            continue
        text = raw_line if comment_start is None else raw_line[:comment_start]
        match = _HEADER_RE.match(text.strip())
        if not match:
            continue
        segments = _parse_key_path(match.group(2))
        headers.append((index, segments[: len(prefix_segments)] == prefix_segments))

    spans: list[tuple[int, int]] = []
    for position, (start, owned) in enumerate(headers):
        if not owned:
            continue
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        if spans and spans[-1][1] == start:
            spans[-1] = (spans[-1][0], end)
        else:
            spans.append((start, end))
    return spans


def _scan_line(
    line: str, depth: int, in_multiline_basic: bool, in_multiline_literal: bool,
) -> tuple[int, bool, bool, int | None]:
    """Advances TOML lexer state across one physical line.

    Returns the updated bracket depth, multi-line string flags, and the
    index of an unquoted ``#`` comment start on this line (``None`` when the
    line has no such comment, e.g. because it is entirely inside a string).
    """

    index = 0
    length = len(line)
    comment_start: int | None = None
    while index < length:
        if in_multiline_literal:
            if line.startswith("'''", index):
                in_multiline_literal = False
                index += 3
            else:
                index += 1
            continue
        if in_multiline_basic:
            if line[index] == "\\" and index + 1 < length:
                index += 2
                continue
            if line.startswith('"""', index):
                in_multiline_basic = False
                index += 3
            else:
                index += 1
            continue
        char = line[index]
        if char == "#":
            comment_start = index
            break
        if line.startswith('"""', index):
            in_multiline_basic = True
            index += 3
            continue
        if line.startswith("'''", index):
            in_multiline_literal = True
            index += 3
            continue
        if char == '"':
            index += 1
            while index < length:
                if line[index] == "\\" and index + 1 < length:
                    index += 2
                    continue
                if line[index] == '"':
                    index += 1
                    break
                index += 1
            continue
        if char == "'":
            index += 1
            while index < length and line[index] != "'":
                index += 1
            index += 1
            continue
        if char == "[":
            depth += 1
            index += 1
            continue
        if char == "]":
            depth = max(0, depth - 1)
            index += 1
            continue
        index += 1
    return depth, in_multiline_basic, in_multiline_literal, comment_start


def _parse_key_path(path: str) -> list[str]:
    """Splits a (possibly quoted) dotted TOML key path into its segments.

    ``plugins."my.id"`` becomes ``["plugins", "my.id"]`` while the unquoted
    ``plugins.my.id`` becomes three segments — matching TOML semantics,
    where only the quoted form names a single key containing a dot.
    """

    segments: list[str] = []
    index = 0
    length = len(path)
    while index < length:
        while index < length and path[index] in " \t":
            index += 1
        if index >= length:
            break
        if path[index] in "\"'":
            quote = path[index]
            index += 1
            buffer: list[str] = []
            while index < length and path[index] != quote:
                if quote == '"' and path[index] == "\\" and index + 1 < length:
                    buffer.append(path[index + 1])
                    index += 2
                    continue
                buffer.append(path[index])
                index += 1
            segments.append("".join(buffer))
            index += 1
        else:
            start = index
            while index < length and path[index] not in ". \t":
                index += 1
            segments.append(path[start:index])
        while index < length and path[index] in " \t":
            index += 1
        if index < length and path[index] == ".":
            index += 1
    return segments


def _append_table(config_toml: str, block: str) -> str:
    if not config_toml.strip():
        return block
    separator = "" if config_toml.endswith("\n") else "\n"
    return f"{config_toml}{separator}\n{block}"


def _render_table(plugin_id: str, values: dict[str, Any]) -> str:
    """Dumps ``values`` as ``[plugins.<plugin_id>...]`` header(s) plus fields.

    The per-line header rewrite below is safe only because ``toml.dumps``
    never emits a multi-line value: strings are written with their newlines
    escaped, so no value line can be mistaken for a table header. ``values``
    is always a validated ``model_dump(mode="json")`` result, which is why the
    naive line scan is sufficient here but not in ``_locate_table``, where the
    input is a user-authored document.
    """

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
