import re

CHECKBOX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[( |x|X)\](?:\s|$)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def count_checkboxes(text: str) -> tuple[int, int]:
    """Returns (done, total) checkbox counts, ignoring fenced code blocks."""
    done = 0
    total = 0
    fence: str | None = None

    for line in text.splitlines():
        if fence is not None:
            # A fence closes on the same character, at least as long as the opener
            if re.fullmatch(rf"\s*{re.escape(fence[0])}{{{len(fence)},}}\s*", line):
                fence = None
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            continue

        box_match = CHECKBOX_RE.match(line)
        if box_match:
            total += 1
            if box_match.group(1) in ("x", "X"):
                done += 1

    return done, total
