import argparse
import os
import shutil
import sys

from checkmarks.collect import collect
from checkmarks.parse import Item, parse_file
from checkmarks.render import render_json, render_pretty, render_tsv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="checkmarks", description="Show progress for Markdown checklists"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="files or directories to read; - reads paths from stdin "
        "(default: $CHECKMARKS_DIR, else the current directory)",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="descend into subdirectories"
    )
    parser.add_argument(
        "--all", action="store_true", help="show empty files found in directories"
    )
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument(
        "--format",
        choices=["pretty", "tsv", "json"],
        help="output format (default: pretty on a terminal, else tsv)",
    )
    fmt.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="same as --format json",
    )
    parser.add_argument("--no-color", action="store_true", help="disable colour")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="warn about empty files"
    )
    return parser


def warn(message: str) -> None:
    print(f"checkmarks: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI. Returns the exit code."""
    args = build_parser().parse_args(argv)

    sources, warnings = collect(args.paths, args.recursive, sys.stdin, os.environ)
    for warning in warnings:
        warn(warning)

    items: list[Item] = []
    for source in sources:
        item = parse_file(source.path)
        if item.status == "error" or (item.status == "empty" and args.verbose):
            warn(f"{item.path}: {item.message}")
        if item.status == "empty" and not source.explicit and not args.all:
            continue
        items.append(item)

    is_tty = sys.stdout.isatty()
    fmt = args.format or ("pretty" if is_tty else "tsv")
    if fmt == "json":
        output = render_json(items)
    elif fmt == "tsv":
        output = render_tsv(items)
    else:
        color = is_tty and not args.no_color and not os.environ.get("NO_COLOR")
        width = shutil.get_terminal_size().columns
        output = render_pretty(items, width, color)
    sys.stdout.write(output)

    return 0 if any(item.status == "ok" for item in items) else 1


if __name__ == "__main__":
    raise SystemExit(main())
