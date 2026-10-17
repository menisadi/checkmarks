import re
from pathlib import Path

import pytest

from checkmarks.cli import main, parse_checklist, show_progress


# Pytest can create and manage temporary files/directories via the 'tmp_path' fixture
def test_parse_checklist_no_tasks(tmp_path: Path):
    # Create an empty markdown file
    md_file = tmp_path / "empty_checklist.md"
    md_file.write_text("", encoding="utf-8")

    done, total, title = parse_checklist(md_file)
    assert done == 0
    assert total == 0
    assert title is None


def test_parse_checklist_with_tasks(tmp_path: Path):
    # A sample markdown with tasks and a level-1 heading
    content = """# My Checklist

- [ ] Task 1
- [x] Task 2
- [x] Task 3
- [ ] Task 4
"""
    md_file = tmp_path / "tasks.md"
    md_file.write_text(content, encoding="utf-8")

    done, total, title = parse_checklist(md_file)
    # We expect 2 done tasks, 4 total tasks, and the title "My Checklist"
    assert done == 2
    assert total == 4
    assert title == "My Checklist"


def test_parse_checklist_no_title(tmp_path: Path):
    # A file with tasks but no H1 heading
    content = """- [ ] Task A
- [x] Task B
"""
    md_file = tmp_path / "notitle.md"
    md_file.write_text(content, encoding="utf-8")

    done, total, title = parse_checklist(md_file)
    assert done == 1
    assert total == 2
    assert title is None


def test_show_progress_output(capsys):
    # Test that show_progress prints the correct bar and summary
    show_progress(done=3, total=5, title="Test Title", bar_length=10)

    # capsys captures stdout/stderr output in pytest
    captured = capsys.readouterr()
    output = captured.out

    # Check that certain strings/patterns appear in the output
    assert "Test Title" in output
    assert "3/5 tasks completed" in output
    # Check for the ASCII bar
    # We expect 3 out of 5 => 60%, so bar_length=10 => 6 "█" if rounding down
    # Actually the code does integer math with //, so 3 * 10 // 5 = 6.
    assert re.search(r"\[█{6}-{4}\]", output) is not None
    assert "(60.0%)" in output


@pytest.mark.parametrize(
    "done,total,percent_str",
    [
        (0, 0, "(0.0%)"),  # edge case: no tasks
        (0, 5, "(0.0%)"),  # none done
        (5, 5, "(100.0%)"),  # all done
    ],
)
def test_show_progress_edge_cases(done, total, percent_str, capsys):
    show_progress(done, total, title=None, bar_length=10)
    output = capsys.readouterr().out
    # Just check the percentage part is correct
    assert percent_str in output


def test_main_file_not_found(monkeypatch, capsys):
    # We'll pretend the user ran: `checklist not_a_file.md`
    test_args = ["checklist", "not_a_file.md"]
    monkeypatch.setattr("sys.argv", test_args)

    main()
    output = capsys.readouterr().out
    assert "❌ File not found: not_a_file.md" in output


def test_main_valid_file(monkeypatch, capsys, tmp_path):
    # Create a temporary markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\n- [ ] One\n- [x] Two", encoding="utf-8")

    # We'll pretend the user ran: `checklist test.md`
    test_args = ["checklist", str(md_file)]
    monkeypatch.setattr("sys.argv", test_args)

    main()
    output = capsys.readouterr().out
    assert "Title" in output
    assert "1/2 tasks completed" in output
