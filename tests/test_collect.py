import io
from pathlib import Path

import pytest

from checkmarks.collect import Source, collect

NO_STDIN = io.StringIO("")


def make_tree(root: Path, files: list[str]) -> None:
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("- [ ] a\n", encoding="utf-8")


def names(sources: list[Source], root: Path) -> list[str]:
    return [s.path.relative_to(root).as_posix() for s in sources]


def test_directory_sorted_and_filtered(tmp_path: Path) -> None:
    make_tree(tmp_path, ["b.md", "a.md", "C.MD", "d.Markdown", "e.txt", "sub/f.md"])
    sources, warnings = collect([str(tmp_path)], False, NO_STDIN, {})
    assert names(sources, tmp_path) == ["C.MD", "a.md", "b.md", "d.Markdown"]
    assert not any(s.explicit for s in sources)
    assert warnings == []


def test_recursive_skips_dot_directories(tmp_path: Path) -> None:
    make_tree(
        tmp_path, ["a.md", "sub/b.md", "sub/deep/c.md", ".git/d.md", "sub/.obs/e.md"]
    )
    sources, _ = collect([str(tmp_path)], True, NO_STDIN, {})
    assert names(sources, tmp_path) == ["a.md", "sub/b.md", "sub/deep/c.md"]


def test_explicit_file_any_extension(tmp_path: Path) -> None:
    make_tree(tmp_path, ["notes.txt"])
    sources, _ = collect([str(tmp_path / "notes.txt")], False, NO_STDIN, {})
    assert sources == [Source(tmp_path / "notes.txt", True)]


def test_input_order_kept_across_args(tmp_path: Path) -> None:
    make_tree(tmp_path, ["z.md", "dir/a.md"])
    args = [str(tmp_path / "z.md"), str(tmp_path / "dir")]
    sources, _ = collect(args, False, NO_STDIN, {})
    assert names(sources, tmp_path) == ["z.md", "dir/a.md"]


def test_path_kept_as_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_tree(tmp_path, ["notes/a.md"])
    monkeypatch.chdir(tmp_path)
    sources, _ = collect(["notes"], False, NO_STDIN, {})
    assert [str(s.path) for s in sources] == [str(Path("notes/a.md"))]


def test_missing_path_warns_and_continues(tmp_path: Path) -> None:
    make_tree(tmp_path, ["a.md"])
    missing = str(tmp_path / "nope.md")
    sources, warnings = collect([missing, str(tmp_path)], False, NO_STDIN, {})
    assert names(sources, tmp_path) == ["a.md"]
    assert warnings == [f"{missing}: no such file or directory"]


def test_stdin_paths(tmp_path: Path) -> None:
    make_tree(tmp_path, ["a.md", "dir/b.md"])
    stdin = io.StringIO(f"{tmp_path / 'a.md'}\n\n  \n{tmp_path / 'dir'}\n")
    sources, _ = collect(["-"], False, stdin, {})
    assert [(n, s.explicit) for n, s in zip(names(sources, tmp_path), sources)] == [
        ("a.md", True),
        ("dir/b.md", False),
    ]


def test_stdin_not_read_without_dash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_tree(tmp_path, ["a.md"])
    monkeypatch.chdir(tmp_path)
    stdin = io.StringIO("other.md\n")
    sources, warnings = collect([], False, stdin, {})
    assert [str(s.path) for s in sources] == ["a.md"]
    assert warnings == []


def test_env_dir_used_without_args(tmp_path: Path) -> None:
    make_tree(tmp_path, ["a.md"])
    sources, _ = collect([], False, NO_STDIN, {"CHECKMARKS_DIR": str(tmp_path)})
    assert names(sources, tmp_path) == ["a.md"]
    assert not sources[0].explicit


def test_env_dir_ignored_with_args(tmp_path: Path) -> None:
    make_tree(tmp_path, ["env/a.md", "arg/b.md"])
    env = {"CHECKMARKS_DIR": str(tmp_path / "env")}
    sources, _ = collect([str(tmp_path / "arg")], False, NO_STDIN, env)
    assert names(sources, tmp_path) == ["arg/b.md"]


def test_cwd_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_tree(tmp_path, ["a.md"])
    monkeypatch.chdir(tmp_path)
    sources, _ = collect([], False, NO_STDIN, {})
    assert sources == [Source(Path("a.md"), False)]


def test_dedupe_first_position_wins(tmp_path: Path) -> None:
    make_tree(tmp_path, ["a.md", "b.md"])
    args = [str(tmp_path / "b.md"), str(tmp_path), str(tmp_path / "b.md")]
    sources, _ = collect(args, False, NO_STDIN, {})
    assert names(sources, tmp_path) == ["b.md", "a.md"]


def test_dedupe_explicit_mention_wins(tmp_path: Path) -> None:
    make_tree(tmp_path, ["a.md"])
    args = [str(tmp_path), str(tmp_path / "a.md")]
    sources, _ = collect(args, False, NO_STDIN, {})
    assert sources == [Source(tmp_path / "a.md", True)]


def test_dedupe_by_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_tree(tmp_path, ["a.md"])
    monkeypatch.chdir(tmp_path)
    sources, _ = collect(
        ["a.md", "./a.md", str(tmp_path / "a.md")], False, NO_STDIN, {}
    )
    assert sources == [Source(Path("a.md"), True)]
