import pytest

from checkmarks.parse import count_checkboxes


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
