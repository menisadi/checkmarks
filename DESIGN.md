# checkmarks v0.2 — progress dashboard

## Goal

Turn `checkmarks` from "progress bar for one Markdown checklist" into a small
dashboard: point it at a folder of Markdown files (books, courses, tutorials)
and get one progress row per file.

Design principle: plain-text files are the source of truth. checkmarks only
reads and reports. It never writes to tracked files and keeps no state of its
own. Pretty output for humans, plain output for pipes.

## Current state (v0.1.1)

- A package `checkmarks/` (flat layout) with entry point
  `checkmarks = checkmarks.cli:main`
- Counts `- [ ]` / `- [x]` occurrences
- Title from the first `# Heading`
- Prints one progress bar
- Basic tests in `tests/test_cli.py`
- Published on PyPI as `checkmarks`
- A `beta/` folder with earlier experiments (`main.py`, `main2.py`)

## Non-goals for v0.2

- Editing or updating files (use `$EDITOR`)
- History, streaks, stats over time (git already has the history)
- Reminders, notifications, a database, a web UI

---

## 1. File format

Files are read as UTF-8. A leading BOM is stripped, and CRLF line endings are
treated the same as LF.

### 1.1 Checklist mode (default)

A file is tracked by counting its checkboxes.

- Matches list items, both bulleted and ordered (`1.` and `1)`):
  `^\s*(?:[-*+]|\d+[.)])\s+\[( |x|X)\](?:\s|$)`
- `[x]` and `[X]` count as done; `[ ]` counts as pending
- Nested items count the same as top-level ones
- Checkboxes inside fenced code blocks are ignored. A fence opens on a line
  whose first non-whitespace characters are 3 or more `` ` `` or `~`. It closes
  on a line made of the same character, at least as long as the opener. An
  unclosed fence runs to the end of the file.
- `unit` defaults to `tasks`

### 1.2 Counter mode (frontmatter override)

If the file has frontmatter with a `progress:` key, that value drives the row
and the checkboxes are ignored for the bar.

```markdown
---
progress: 143/320
unit: pages
---
# Dune
- [x] Book One
- [ ] Book Two
```

Frontmatter rules:

- It's only recognised if line 1 is exactly `---`; it runs until the next
  `---` line. If there is no closing `---`, the file has no frontmatter and
  is parsed as plain Markdown.
- It's flat `key: value` lines, parsed by hand. No PyYAML; the package stays
  dependency-free.
  - Each line is split on the first `:`, so `title: Dune: Part One` works.
  - Keys and values are stripped of surrounding whitespace.
  - A value wrapped in matching single or double quotes has them removed.
  - Lines without a `:` are ignored.
- Keys:
  - `progress`: `N/M`, non-negative integers, whitespace around `/` allowed
  - `unit`: free text, display only (default `tasks` in checklist mode,
    `units` in counter mode if omitted)
  - `title`: overrides the heading-derived title
- Unknown keys are ignored silently, so they stay free for future features.

### 1.3 Title resolution

The title is chosen in this order:

1. Frontmatter `title`
2. The first `# Heading` line outside frontmatter and fenced code blocks
3. The filename stem

### 1.4 Status

Every row has a `mode` (`checklist` or `counter`) and a `status`:

- `ok`: valid counts.
- `empty`: a checklist-mode file with zero checkboxes. No warning by default;
  a warning on stderr under `--verbose`.
- `error`: the row is still emitted, and a warning is printed on stderr.
  Causes:
  - The file can't be read or isn't valid UTF-8 (mode `checklist`)
  - `progress` is unparseable (mode `counter`)
  - `M == 0` (mode `counter`)
  - `N > M` (mode `counter`)

For `empty` and `error` rows, `done`, `total` and `pct` are unset (`null` in
JSON, empty fields in TSV).

---

## 2. CLI

```
checkmarks [PATH ...] [-r] [--all] [--format {pretty,tsv,json}] [--json] [--no-color] [-v]
```

### Input resolution

- Each PATH can be a file, a directory, or `-`.
- `-` reads paths from stdin, one per line (blank lines skipped). Stdin is
  never read implicitly.
- For a directory, files directly inside whose extension is `.md` or
  `.markdown` (case-insensitive) are read, sorted by path.
  - `-r/--recursive` descends into subdirectories.
  - Directories whose names start with `.` (e.g. `.git`, `.obsidian`) are
    skipped.
- With no PATH arguments:
  - Use `$CHECKMARKS_DIR` if set.
  - Else use the current directory.
- Rows are output in input order. Within a directory, they're sorted by path.
- Duplicates are dropped by resolved path; the first occurrence wins.
- A nonexistent path produces a warning on stderr; processing continues.

### Visibility

- Files found by expanding a directory (including `$CHECKMARKS_DIR` and the
  current directory) are hidden when their status is `empty`. This applies to
  all formats.
- `--all` shows them.
- Files named explicitly, as arguments or via `-`, are always shown.

### Output format selection

- `--format` / `--json` is given: use it.
- Otherwise, stdout is a TTY: `pretty`.
- Otherwise: `tsv`.

### Exit codes

- `0`: at least one row has status `ok`. Per-file warnings don't change this.
- `1`: no row has status `ok`. This covers no files found, only bad paths,
  all rows `error`, and all rows `empty`.
- `2`: usage error (argparse default).

---

## 3. Output formats

### 3.1 pretty

```
Thinking, Fast and Slow   [█████-----]  143/320 pages   45%
Gödel, Escher, Bach       [██--------]  180/777 pages   23%
Rust tutorial             [████------]   12/28  tasks   43%
NN hands-on               [███-------]    2/8   tasks   25%
Broken file               [    ?     ]    ?             ?
```

- Columns are aligned and titles are truncated with `…` to fit.
- Alignment and truncation use display width, computed with
  `unicodedata.east_asian_width` (wide and fullwidth characters count as 2).
  Imperfect handling of emoji and ZWJ sequences is acceptable.
- Bar width adapts to `shutil.get_terminal_size()`, with a minimum of 10.
- The filled part of the bar is floored, so the bar is only full at 100%.
- Colour is optional (for example, green at 100%). It's disabled by
  `--no-color`, by the `NO_COLOR` env var, or when stdout isn't a TTY.

### 3.2 tsv

One row per file, no header, tab-separated:

```
title    done    total    pct    unit    mode    status    path
```

- `pct` has one decimal place.
- `mode` is `checklist` or `counter`; `status` is `ok`, `empty` or `error`.
- `empty` and `error` rows have empty `done`/`total`/`pct` fields.
- Tabs and newlines in titles are replaced with spaces.
- `path` is printed as given (not resolved).

### 3.3 json

A JSON array of objects:

```json
{
  "title": "Dune",
  "done": 143,
  "total": 320,
  "pct": 44.7,
  "unit": "pages",
  "mode": "counter",
  "status": "ok",
  "path": "progress/dune.md"
}
```

- `status` is one of `ok`, `empty`, `error`.
- `empty` and `error` rows have `done`, `total` and `pct` set to `null`.
- Error rows include a `"message"` field.
- `path` is printed as given (not resolved).

---

## 4. Package layout

```
checkmarks/
├── pyproject.toml          # requires-python >=3.11; entry point: checkmarks = checkmarks.cli:main
├── README.md
├── DESIGN.md
├── src/checkmarks/
│   ├── __init__.py         # __version__
│   ├── parse.py            # frontmatter + checkbox parsing → Item dataclass
│   ├── collect.py          # path resolution (files, dirs, stdin, env)
│   ├── render.py           # pretty / tsv / json renderers
│   └── cli.py              # argparse, wiring, exit codes
└── tests/
    ├── fixtures/           # sample .md files
    ├── test_parse.py
    ├── test_collect.py
    └── test_render.py
```

Parsing returns pure data:

```python
@dataclass
class Item:
    path: Path
    title: str
    done: int | None
    total: int | None
    unit: str
    mode: Literal["checklist", "counter"]
    status: Literal["ok", "empty", "error"]
    message: str | None = None
```

Renderers take `list[Item]` and return a string. There's no I/O in `parse.py`
beyond reading the given file, and none at all in `render.py`.

Target Python 3.11+, standard library only.

---

## 5. Compatibility

- `checkmarks file.md` keeps working, but output becomes a one-row table
  instead of the old block with the bold title line and "N/M tasks completed".
  This is a breaking output change, so release it as 0.2.0 (from 0.1.1) and
  note it in the README.
- Plain checklist files from v0.1 need no changes.
- Minimum Python becomes 3.11.

---

## 6. Implementation plan

1. Move to the `src/` layout and add `requires-python = ">=3.11"`. Remove
   `beta/` after confirming nothing in it is missing from `cli.py`. Port the
   existing logic unchanged and add tests for current behaviour.
2. Add `parse.py` checkbox rules: bullet and ordered variants, `[X]`,
   `(\s|$)` after the bracket, ignoring fenced code.
3. Add frontmatter parsing, title resolution and counter mode, with the
   status rules from §1.4.
4. Add `collect.py`: multiple paths, directories, `-r`, `-`,
   `$CHECKMARKS_DIR`, dot-directory skipping, dedupe, extension matching.
5. Add renderers in this order: tsv → json → pretty, with TTY auto-detection.
6. Add `--all` visibility rules, exit codes and stderr warnings.
7. Update the README with format spec and examples, bump to 0.2.0, then
   publish.

Each step should land with tests. Pretty output tests should force a fixed
terminal width.

---

## 7. Future ideas (not v0.2)

- `checkmarks bump FILE N`: a separate tiny command to increment `progress`
- A secondary column showing chapter checkboxes in counter mode ("ch 1/3")
- A `last updated` column from file mtime, to highlight stalled items
- `archived: true` frontmatter key (or `--hide-done`) to drop finished items
- An `icon:` frontmatter key for per-row emoji
- A pace and history report built from `git log` of the progress folder, as a
  separate script
