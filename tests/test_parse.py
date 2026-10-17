from pathlib import Path

import pytest

from checkmarks.parse import (
    Item,
    count_checkboxes,
    find_heading,
    parse_file,
    parse_frontmatter,
    parse_progress,
)


@pytest.mark.parametrize(
    "line,expected",
    [
        ("- [ ] task", (0, 1)),
        ("- [x] task", (1, 1)),
        ("- [X] task", (1, 1)),
        ("* [x] task", (1, 1)),
        ("+ [x] task", (1, 1)),
        ("1. [x] task", (1, 1)),
        ("12) [ ] task", (0, 1)),
        ("- [x]", (1, 1)),  # bare checkbox at end of line
        ("- [x]\ttask", (1, 1)),
        ("    - [x] nested", (1, 1)),
        ("-  [x] extra spaces", (1, 1)),
    ],
)
def test_checkbox_variants(line: str, expected: tuple[int, int]) -> None:
    assert count_checkboxes(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "Some prose with - [ ] inline",
        "-[x] no space after marker",
        "- [x]task no space after bracket",
        "- [y] wrong mark",
        "- [] empty brackets",
        "1 [x] no dot",
        "a. [x] letter marker",
    ],
)
def test_non_checkboxes(line: str) -> None:
    assert count_checkboxes(line) == (0, 0)


def test_mixed_list() -> None:
    text = "# Title\n- [ ] a\n- [x] b\n  * [X] c\n1. [ ] d\n"
    assert count_checkboxes(text) == (2, 4)


def test_crlf_line_endings() -> None:
    assert count_checkboxes("- [x] a\r\n- [ ] b\r\n") == (1, 2)


@pytest.mark.parametrize("fence", ["```", "~~~", "````", "```python"])
def test_fenced_code_ignored(fence: str) -> None:
    closer = fence.rstrip("python")
    text = f"- [x] a\n{fence}\n- [ ] in code\n{closer}\n- [ ] b\n"
    assert count_checkboxes(text) == (1, 2)


def test_indented_fence_ignored() -> None:
    text = "- [x] a\n  ```\n  - [ ] in code\n  ```\n- [ ] b\n"
    assert count_checkboxes(text) == (1, 2)


def test_fence_closes_only_on_same_char() -> None:
    text = "```\n~~~\n- [ ] still code\n```\n- [x] a\n"
    assert count_checkboxes(text) == (1, 1)


def test_fence_closes_only_on_equal_or_longer() -> None:
    text = "````\n```\n- [ ] still code\n`````\n- [x] a\n"
    assert count_checkboxes(text) == (1, 1)


def test_fence_closer_with_text_does_not_close() -> None:
    text = "```\n``` not a closer\n- [ ] still code\n```\n- [x] a\n"
    assert count_checkboxes(text) == (1, 1)


def test_unclosed_fence_runs_to_end() -> None:
    text = "- [x] a\n```\n- [ ] in code\n- [ ] in code\n"
    assert count_checkboxes(text) == (1, 1)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_frontmatter_basic() -> None:
    meta, body_start = parse_frontmatter(["---", "progress: 1/2", "---", "# T"])
    assert meta == {"progress": "1/2"}
    assert body_start == 3


def test_parse_frontmatter_requires_first_line() -> None:
    assert parse_frontmatter(["", "---", "a: b", "---"]) == ({}, 0)
    assert parse_frontmatter(["--- ", "a: b", "---"]) == ({}, 0)


def test_parse_frontmatter_splits_on_first_colon_and_skips_bad_lines() -> None:
    meta, _ = parse_frontmatter(
        ["---", "title: A: B", "no colon", "  k  :  v  ", "---"]
    )
    assert meta == {"title": "A: B", "k": "v"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ('"quoted"', "quoted"),
        ("'single'", "single"),
        ("\"mismatched'", "\"mismatched'"),
        ('"', '"'),
    ],
)
def test_parse_frontmatter_quotes(value: str, expected: str) -> None:
    meta, _ = parse_frontmatter(["---", f"title: {value}", "---"])
    assert meta["title"] == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("143/320", (143, 320)),
        ("143 / 320", (143, 320)),
        ("0/5", (0, 5)),
        ("5/5", (5, 5)),
    ],
)
def test_parse_progress_valid(value: str, expected: tuple[int, int]) -> None:
    assert parse_progress(value) == expected


@pytest.mark.parametrize("value", ["", "half", "1/", "/2", "-1/5", "1.5/3", "1/2/3"])
def test_parse_progress_unparseable(value: str) -> None:
    assert isinstance(parse_progress(value), str)


def test_parse_progress_zero_total() -> None:
    assert parse_progress("0/0") == "progress total is 0"


def test_parse_progress_done_exceeds_total() -> None:
    assert parse_progress("6/5") == "progress 6/5 exceeds total"


def test_find_heading_skips_fences() -> None:
    assert find_heading(["```", "# comment", "```", "# Real"]) == "Real"
    assert find_heading(["## Sub", "no heading"]) is None


def test_file_counter_mode() -> None:
    item = parse_file(FIXTURES / "counter.md")
    assert item == Item(
        FIXTURES / "counter.md", "Dune", 143, 320, "pages", "counter", "ok"
    )


def test_file_bom_and_crlf() -> None:
    item = parse_file(FIXTURES / "bom_crlf.md")
    assert (item.title, item.done, item.total, item.status) == ("BOM file", 1, 2, "ok")


def test_file_unclosed_frontmatter_is_markdown() -> None:
    item = parse_file(FIXTURES / "unclosed_frontmatter.md")
    assert item.title == "unclosed_frontmatter"
    assert (item.done, item.total, item.mode) == (1, 2, "checklist")


def test_file_frontmatter_title_wins_over_heading() -> None:
    item = parse_file(FIXTURES / "quoted_title.md")
    assert item.title == "Dune: Part One"
    assert item.unit == "chapters"
    assert item.mode == "checklist"


def test_file_bad_progress_is_error() -> None:
    item = parse_file(FIXTURES / "bad_progress.md")
    assert (item.mode, item.status) == ("counter", "error")
    assert (item.done, item.total) == (None, None)
    assert item.title == "Bad progress"
    assert item.unit == "units"
    assert item.message is not None


def test_file_without_checkboxes_is_empty() -> None:
    item = parse_file(FIXTURES / "empty.md")
    assert (item.mode, item.status, item.done, item.total) == (
        "checklist",
        "empty",
        None,
        None,
    )
    assert item.unit == "tasks"


def test_file_heading_inside_fence_is_not_title() -> None:
    item = parse_file(FIXTURES / "heading_in_fence.md")
    assert item.title == "Real title"
    assert (item.done, item.total) == (0, 1)


def test_file_missing_is_error(tmp_path: Path) -> None:
    item = parse_file(tmp_path / "missing.md")
    assert (item.mode, item.status, item.title) == ("checklist", "error", "missing")


def test_file_invalid_utf8_is_error(tmp_path: Path) -> None:
    md_file = tmp_path / "latin1.md"
    md_file.write_bytes(b"- [x] caf\xe9\n")
    item = parse_file(md_file)
    assert item.status == "error"


def test_file_empty_progress_value_is_error(tmp_path: Path) -> None:
    md_file = tmp_path / "p.md"
    md_file.write_text("---\nprogress:\n---\n- [x] a\n", encoding="utf-8")
    item = parse_file(md_file)
    assert (item.mode, item.status) == ("counter", "error")
