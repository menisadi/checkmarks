import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

MARKDOWN_SUFFIXES = {".md", ".markdown"}


@dataclass
class Source:
    path: Path
    explicit: bool


def expand_dir(directory: Path, recursive: bool) -> list[Path]:
    """Returns the Markdown files in a directory, sorted by path."""
    found: list[Path] = []
    for root, dirnames, filenames in os.walk(directory):
        if recursive:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        else:
            dirnames[:] = []
        root_path = Path(root)
        found.extend(
            root_path / name
            for name in filenames
            if Path(name).suffix.lower() in MARKDOWN_SUFFIXES
        )
    return sorted(found)


def iter_args(paths: list[str], stdin: TextIO, env: Mapping[str, str]) -> Iterator[str]:
    """Yields path arguments, expanding `-` and applying the no-argument default."""
    if not paths:
        yield env.get("CHECKMARKS_DIR") or "."
        return

    for arg in paths:
        if arg == "-":
            yield from (line.strip() for line in stdin if line.strip())
        else:
            yield arg


def collect(
    paths: list[str], recursive: bool, stdin: TextIO, env: Mapping[str, str]
) -> tuple[list[Source], list[str]]:
    """Resolves path arguments into sources, plus warnings for bad paths."""
    sources: list[Source] = []
    warnings: list[str] = []
    seen: dict[Path, Source] = {}

    def add(path: Path, explicit: bool) -> None:
        key = path.resolve()
        if key in seen:
            # The first position wins, but an explicit mention always counts
            seen[key].explicit = seen[key].explicit or explicit
            return
        source = Source(path, explicit)
        seen[key] = source
        sources.append(source)

    for arg in iter_args(paths, stdin, env):
        path = Path(arg)
        if path.is_dir():
            for file in expand_dir(path, recursive):
                add(file, explicit=False)
        elif path.exists():
            add(path, explicit=True)
        else:
            warnings.append(f"{arg}: no such file or directory")

    return sources, warnings
