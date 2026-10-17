import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CHECKBOX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[( |x|X)\](?:\s|$)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^#\s+(.+)")
PROGRESS_RE = re.compile(r"^(\d+)\s*/\s*(\d+)$")


@dataclass
class Item:
    path: Path
    title: str
    done: int | None
    total: int | None
    unit: str
    mode: Literal["checklist", "counter"]
    status: Literal["ok", "empty", "error"]
    message: str | None = None


def unfenced_lines(lines: Iterable[str]) -> Iterator[str]:
    """Yields the lines that are outside fenced code blocks."""
    fence: str | None = None

    for line in lines:
        if fence is not None:
            # A fence closes on the same character, at least as long as the opener
            if re.fullmatch(rf"\s*{re.escape(fence[0])}{{{len(fence)},}}\s*", line):
                fence = None
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            continue

        yield line


def count_checkboxes(text: str) -> tuple[int, int]:
    """Returns (done, total) checkbox counts, ignoring fenced code blocks."""
    done = 0
    total = 0

    for line in unfenced_lines(text.splitlines()):
        box_match = CHECKBOX_RE.match(line)
        if box_match:
            total += 1
            if box_match.group(1) in ("x", "X"):
                done += 1

    return done, total


def find_heading(lines: Iterable[str]) -> str | None:
    """Returns the first level-1 heading outside fenced code blocks."""
    for line in unfenced_lines(lines):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            return heading_match.group(1).strip()
    return None


def parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Returns (frontmatter keys, index of the first body line)."""
    if not lines or lines[0] != "---":
        return {}, 0

    try:
        end = lines.index("---", 1)
    except ValueError:
        # No closing delimiter: the file has no frontmatter
        return {}, 0

    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value

    return meta, end + 1


def parse_progress(value: str) -> tuple[int, int] | str:
    """Returns (done, total), or an error message if the value is invalid."""
    progress_match = PROGRESS_RE.match(value)
    if not progress_match:
        return f"unparseable progress: {value!r}"

    done, total = int(progress_match.group(1)), int(progress_match.group(2))
    if total == 0:
        return "progress total is 0"
    if done > total:
        return f"progress {done}/{total} exceeds total"
    return done, total


def parse_file(path: Path) -> Item:
    """Parses a Markdown file into an Item."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        return Item(
            path=path,
            title=path.stem,
            done=None,
            total=None,
            unit="tasks",
            mode="checklist",
            status="error",
            message=str(e),
        )

    lines = text.splitlines()
    meta, body_start = parse_frontmatter(lines)
    body = lines[body_start:]
    title = meta.get("title") or find_heading(body) or path.stem

    if "progress" in meta:
        unit = meta.get("unit") or "units"
        progress = parse_progress(meta["progress"])
        if isinstance(progress, str):
            return Item(path, title, None, None, unit, "counter", "error", progress)
        done, total = progress
        return Item(path, title, done, total, unit, "counter", "ok")

    unit = meta.get("unit") or "tasks"
    done, total = count_checkboxes("\n".join(body))
    if total == 0:
        return Item(
            path, title, None, None, unit, "checklist", "empty", "no checkboxes found"
        )
    return Item(path, title, done, total, unit, "checklist", "ok")
