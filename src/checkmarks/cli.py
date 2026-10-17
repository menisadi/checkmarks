import argparse
import re
from pathlib import Path

from checkmarks.parse import count_checkboxes

CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def parse_checklist(file_path: Path) -> tuple[int, int, str | None]:
    """Parses a markdown checklist file and returns task counts and optional title."""
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()

    done, total = count_checkboxes(content)

    # Try to extract the first level-1 heading as the title
    title_match = re.search(r"^# (.+)", content, re.MULTILINE)
    title: str | None = title_match.group(1).strip() if title_match else None

    return done, total, title


def show_progress(
    done: int, total: int, title: str | None = None, bar_length: int = 40
) -> None:
    """Displays a progress bar in the terminal, optionally with a custom title."""
    percent: float = (done / total) * 100 if total else 0
    filled_length: int = int(bar_length * done // total) if total else 0
    bar: str = "█" * filled_length + "-" * (bar_length - filled_length)

    heading: str = (
        f"{BOLD}{CYAN}{title}{RESET}"
        if title
        else f"{BOLD}{CYAN}Checklist Progress{RESET}"
    )
    print(f"\n{heading}")
    print(f"[{bar}] {done}/{total} tasks completed ({percent:.1f}%)\n")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Track Markdown checklist progress")
    parser.add_argument(
        "markdown_file", type=str, help="Path to your checklist .md file"
    )
    args = parser.parse_args()

    md_path: Path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"❌ File not found: {md_path}")
        return

    done, total, title = parse_checklist(md_path)
    show_progress(done, total, title)


if __name__ == "__main__":
    main()
