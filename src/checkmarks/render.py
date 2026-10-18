import json
import unicodedata

from checkmarks.parse import Item

MIN_BAR = 10
MAX_BAR = 40
GREEN = "\033[32m"
RESET = "\033[0m"


def pct(item: Item) -> float | None:
    """Returns the completion percentage, or None for empty and error rows."""
    if item.status != "ok" or item.done is None or not item.total:
        return None
    return item.done / item.total * 100


def clean(text: str) -> str:
    """Replaces characters that would break a TSV row with spaces."""
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def render_tsv(items: list[Item]) -> str:
    """Renders items as tab-separated rows, without a header."""
    lines = []
    for item in items:
        p = pct(item)
        ok = p is not None
        fields = [
            clean(item.title),
            str(item.done) if ok else "",
            str(item.total) if ok else "",
            f"{p:.1f}" if ok else "",
            clean(item.unit),
            item.status,
            str(item.path),
        ]
        lines.append("\t".join(fields))
    return "".join(line + "\n" for line in lines)


def render_json(items: list[Item]) -> str:
    """Renders items as a JSON array."""
    rows = []
    for item in items:
        p = pct(item)
        ok = p is not None
        row: dict[str, object] = {
            "title": item.title,
            "done": item.done if ok else None,
            "total": item.total if ok else None,
            "pct": round(p, 1) if p is not None else None,
            "unit": item.unit,
            "status": item.status,
            "path": str(item.path),
        }
        if item.status == "error":
            row["message"] = item.message
        rows.append(row)
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def display_width(text: str) -> int:
    """Returns the terminal column width of text (wide chars count as 2)."""
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def ljust(text: str, width: int) -> str:
    return text + " " * (width - display_width(text))


def rjust(text: str, width: int) -> str:
    return " " * (width - display_width(text)) + text


def truncate(text: str, width: int) -> str:
    """Cuts text to fit width, marking the cut with an ellipsis."""
    if display_width(text) <= width:
        return text
    kept = ""
    for char in text:
        if display_width(kept + char) + 1 > width:
            break
        kept += char
    return kept + "…"


def pretty_pct(done: int, total: int) -> int:
    """Rounds the percentage, but only shows 100 when everything is done."""
    p = round(done * 100 / total)
    return 99 if p == 100 and done < total else p


def render_pretty(items: list[Item], width: int, color: bool) -> str:
    """Renders items as an aligned table of progress bars."""
    if not items:
        return ""

    ok_items = [i for i in items if i.status == "ok"]
    done_w = max((len(str(i.done)) for i in ok_items), default=1)
    total_w = max((len(str(i.total)) for i in ok_items), default=0)
    unit_w = max((display_width(i.unit) for i in ok_items), default=0)
    counts_w = done_w + (1 + total_w + 1 + unit_w if ok_items else 0)
    pct_w = 4

    # title + "  [" + bar + "]  " + counts + "  " + pct
    fixed = 3 + 3 + counts_w + 2 + pct_w
    title_w = max(display_width(i.title) for i in items)
    bar_w = min(MAX_BAR, width - fixed - title_w)
    if bar_w < MIN_BAR:
        bar_w = MIN_BAR
        title_w = max(1, width - fixed - bar_w)

    lines = []
    for item in items:
        title = ljust(truncate(item.title, title_w), title_w)
        if item.status == "ok" and item.done is not None and item.total:
            filled = item.done * bar_w // item.total
            bar = "█" * filled + "-" * (bar_w - filled)
            counts = (
                f"{rjust(str(item.done), done_w)}/"
                f"{str(item.total).ljust(total_w)} {ljust(item.unit, unit_w)}"
            )
            p = f"{pretty_pct(item.done, item.total)}%"
        else:
            mark = "?" if item.status == "error" else "—"
            bar = mark.center(bar_w) if item.status == "error" else " " * bar_w
            counts = ljust(rjust(mark, done_w), counts_w)
            p = mark

        line = f"{title}  [{bar}]  {counts}  {rjust(p, pct_w)}"
        if color and item.status == "ok" and item.done == item.total:
            line = f"{GREEN}{line}{RESET}"
        lines.append(line)

    return "".join(line + "\n" for line in lines)
