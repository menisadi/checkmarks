import json
from pathlib import Path

import pytest

from checkmarks.parse import Item
from checkmarks.render import (
    GREEN,
    display_width,
    pretty_pct,
    render_json,
    render_pretty,
    render_tsv,
    truncate,
)

OK = Item(Path("books/dune.md"), "Dune", 143, 320, "pages", "counter", "ok")
EMPTY = Item(
    Path("notes.md"), "Notes", None, None, "tasks", "checklist", "empty", "no boxes"
)
ERROR = Item(Path("bad.md"), "Bad", None, None, "units", "counter", "error", "oops")


def bar_of(line: str) -> str:
    return line[line.index("[") + 1 : line.index("]")]


# --- tsv ---


def test_tsv_rows() -> None:
    assert render_tsv([OK, EMPTY, ERROR]).splitlines() == [
        "Dune\t143\t320\t44.7\tpages\tcounter\tok\tbooks/dune.md",
        "Notes\t\t\t\ttasks\tchecklist\tempty\tnotes.md",
        "Bad\t\t\t\tunits\tcounter\terror\tbad.md",
    ]


def test_tsv_cleans_title_and_unit() -> None:
    item = Item(Path("a.md"), "A\tB\nC\r", 1, 2, "x\ty", "checklist", "ok")
    assert render_tsv([item]) == "A B C \t1\t2\t50.0\tx y\tchecklist\tok\ta.md\n"


def test_tsv_empty_list() -> None:
    assert render_tsv([]) == ""


# --- json ---


def test_json_rows() -> None:
    rows = json.loads(render_json([OK, EMPTY, ERROR]))
    assert rows[0] == {
        "title": "Dune",
        "done": 143,
        "total": 320,
        "pct": 44.7,
        "unit": "pages",
        "mode": "counter",
        "status": "ok",
        "path": "books/dune.md",
    }
    assert rows[1]["done"] is None and rows[1]["pct"] is None
    assert "message" not in rows[1]
    assert rows[2]["total"] is None and rows[2]["message"] == "oops"


def test_json_keeps_unicode() -> None:
    item = Item(Path("g.md"), "Gödel", 1, 2, "pages", "counter", "ok")
    assert "Gödel" in render_json([item])


def test_json_empty_list() -> None:
    assert json.loads(render_json([])) == []


# --- pretty helpers ---


@pytest.mark.parametrize(
    "text,expected",
    [("abc", 3), ("日本", 4), ("ｱ", 1), ("Ａ", 2), ("é", 1), ("", 0)],
)
def test_display_width(text: str, expected: int) -> None:
    assert display_width(text) == expected


def test_truncate() -> None:
    assert truncate("short", 10) == "short"
    assert truncate("exactly10!", 10) == "exactly10!"
    assert truncate("much too long", 8) == "much to…"
    assert truncate("日本語の本", 6) == "日本…"
    assert truncate("日本語の本", 5) == "日本…"


@pytest.mark.parametrize(
    "done,total,expected",
    [(143, 320, 45), (0, 5, 0), (319, 320, 99), (320, 320, 100), (1, 3, 33)],
)
def test_pretty_pct(done: int, total: int, expected: int) -> None:
    assert pretty_pct(done, total) == expected


# --- pretty ---


def test_pretty_spec_example() -> None:
    items = [
        Item(Path("a"), "Thinking, Fast and Slow", 143, 320, "pages", "counter", "ok"),
        Item(Path("b"), "Gödel, Escher, Bach", 180, 777, "pages", "counter", "ok"),
        Item(Path("c"), "Rust tutorial", 12, 28, "tasks", "checklist", "ok"),
        Item(Path("d"), "NN hands-on", 2, 8, "tasks", "checklist", "ok"),
        Item(Path("e"), "Broken file", None, None, "units", "counter", "error"),
    ]
    assert render_pretty(items, 50, False).splitlines() == [
        "Thinking, Fast…  [████------]  143/320 pages   45%",
        "Gödel, Escher,…  [██--------]  180/777 pages   23%",
        "Rust tutorial    [████------]   12/28  tasks   43%",
        "NN hands-on      [██--------]    2/8   tasks   25%",
        "Broken file      [    ?     ]    ?               ?",
    ]


def test_pretty_lines_fit_width() -> None:
    items = [
        OK,
        EMPTY,
        ERROR,
        Item(Path("w"), "日本語の本" * 5, 1, 2, "p", "counter", "ok"),
    ]
    for width in (50, 60, 80):
        lines = render_pretty(items, width, False).splitlines()
        assert all(display_width(line) <= width for line in lines)


def test_pretty_columns_align() -> None:
    items = [OK, EMPTY, ERROR, Item(Path("w"), "日本", 1, 2, "p", "counter", "ok")]
    lines = render_pretty(items, 80, False).splitlines()
    starts = {display_width(line[: line.index("[")]) for line in lines}
    widths = {display_width(line) for line in lines}
    assert len(starts) == 1
    assert len(widths) == 1


def test_pretty_bar_max_width() -> None:
    line = render_pretty([OK], 200, False).splitlines()[0]
    assert len(bar_of(line)) == 40


def test_pretty_bar_min_width() -> None:
    line = render_pretty([OK], 20, False).splitlines()[0]
    assert len(bar_of(line)) == 10


def test_pretty_bar_is_floored() -> None:
    item = Item(Path("a"), "A", 319, 320, "pages", "counter", "ok")
    line = render_pretty([item], 200, False).splitlines()[0]
    assert bar_of(line) == "█" * 39 + "-"
    assert line.endswith(" 99%")


def test_pretty_empty_row() -> None:
    line = render_pretty([OK, EMPTY], 60, False).splitlines()[1]
    assert bar_of(line).strip() == ""
    assert line.endswith("—")
    assert line.count("—") == 2


def test_pretty_only_non_ok_rows() -> None:
    lines = render_pretty([EMPTY, ERROR], 40, False).splitlines()
    assert len(lines) == 2
    assert lines[1].endswith("?")


def test_pretty_color_only_when_complete() -> None:
    complete = Item(Path("a"), "A", 5, 5, "tasks", "checklist", "ok")
    out = render_pretty([OK, complete, ERROR], 60, True).splitlines()
    assert out[1].startswith(GREEN)
    assert "\033[" not in out[0] + out[2]


def test_pretty_no_color() -> None:
    complete = Item(Path("a"), "A", 5, 5, "tasks", "checklist", "ok")
    assert "\033[" not in render_pretty([complete], 60, False)


def test_pretty_empty_list() -> None:
    assert render_pretty([], 80, False) == ""
