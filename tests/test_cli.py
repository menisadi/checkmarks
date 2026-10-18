import json
import sys
from pathlib import Path

import pytest

from checkmarks.cli import main


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A progress folder, used as the current directory."""
    (tmp_path / "a.md").write_text("# Alpha\n- [x] a\n- [ ] b\n", encoding="utf-8")
    (tmp_path / "b.md").write_text(
        "---\nunit: chapters\n---\n# Beta\n- [x] a\n", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("# Notes\nprose\n", encoding="utf-8")
    (tmp_path / "bad.md").write_bytes(b"- [x] caf\xe9\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CHECKMARKS_DIR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLUMNS", "60")
    return tmp_path


def fake_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)


def test_default_is_tsv_when_piped(tree: Path, capsys: pytest.CaptureFixture) -> None:
    assert main([]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "Alpha\t1\t2\t50.0\ttasks\tok\ta.md",
        "Beta\t1\t1\t100.0\tchapters\tok\tb.md",
        "bad\t\t\t\ttasks\terror\tbad.md",
    ]
    assert err.startswith("checkmarks: bad.md: ")


def test_default_is_pretty_on_tty(
    tree: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_tty(monkeypatch)
    main(["a.md", "b.md"])
    out = capsys.readouterr().out
    assert "Alpha" in out and "[" in out
    assert "\033[32m" in out  # Beta is complete


def test_no_color_flag_and_env(
    tree: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_tty(monkeypatch)
    main(["b.md", "--no-color"])
    assert "\033[" not in capsys.readouterr().out
    monkeypatch.setenv("NO_COLOR", "1")
    main(["b.md"])
    assert "\033[" not in capsys.readouterr().out


def test_pretty_when_piped_has_no_color(
    tree: Path, capsys: pytest.CaptureFixture
) -> None:
    main(["b.md", "--format", "pretty"])
    out = capsys.readouterr().out
    assert "\033[" not in out
    assert all(len(line) <= 60 for line in out.splitlines())


def test_json(tree: Path, capsys: pytest.CaptureFixture) -> None:
    main(["--json", "a.md"])
    rows = json.loads(capsys.readouterr().out)
    assert [r["title"] for r in rows] == ["Alpha"]


def test_format_and_json_conflict(tree: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--json", "--format", "tsv"])
    assert exc.value.code == 2


def test_directory_hides_empty_unless_all(
    tree: Path, capsys: pytest.CaptureFixture
) -> None:
    main(["."])
    assert "Notes" not in capsys.readouterr().out
    main([".", "--all"])
    assert "Notes\t\t\t\ttasks\tempty\tnotes.md" in capsys.readouterr().out


def test_explicit_empty_file_shown(tree: Path, capsys: pytest.CaptureFixture) -> None:
    main([".", "notes.md"])
    assert "Notes" in capsys.readouterr().out


def test_verbose_warns_about_empty(tree: Path, capsys: pytest.CaptureFixture) -> None:
    main(["a.md", "notes.md"])
    assert "notes.md" not in capsys.readouterr().err
    main(["-v", "."])
    assert "checkmarks: notes.md: no checkboxes found" in capsys.readouterr().err


def test_missing_file_warns(tree: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["nope.md", "a.md"]) == 0
    assert capsys.readouterr().err == "checkmarks: nope.md: no such file or directory\n"


@pytest.mark.parametrize(
    "args", [["nope.md"], ["notes.md"], ["bad.md"], ["--all", "notes.md", "bad.md"]]
)
def test_exit_1_without_ok_rows(tree: Path, args: list[str]) -> None:
    assert main(args) == 1


def test_exit_1_for_empty_directory(tmp_path: Path) -> None:
    assert main([str(tmp_path)]) == 1


def test_stdin_paths(
    tree: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("b.md\n"))
    main(["-"])
    assert capsys.readouterr().out.startswith("Beta\t")


def test_env_dir(
    tree: Path,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = tmp_path_factory.mktemp("other")
    (other / "c.md").write_text("# Gamma\n- [ ] a\n", encoding="utf-8")
    monkeypatch.setenv("CHECKMARKS_DIR", str(other))
    main([])
    assert capsys.readouterr().out.startswith("Gamma\t")
