# Checkmarks

A small command-line dashboard for your progress. Point it at a folder of Markdown files (books, courses, tutorials) and get one progress bar per file.

```
$ checkmarks ~/progress
Thinking, Fast and Slow  [████------]  17/38 chapters   45%
Gödel, Escher, Bach      [██--------]   5/22 chapters   23%
Rust tutorial            [████------]  12/28 tasks      43%
NN hands-on              [██--------]   2/8  tasks      25%
```

Your Markdown files are the source of truth: checkmarks only reads and reports. It never changes your files and keeps no state of its own.

## Installation

### Option 1: Install via PyPI (Recommended)
```bash
pip install checkmarks
```

### Option 2: Install from source

1. Make sure you have Python 3.11+ installed.
2. Clone or download this repository.
```bash
git clone https://github.com/menisadi/checkmarks.git
cd checkmarks
pip install .
```

## Usage

```bash
checkmarks todo.md               # one file
checkmarks ~/progress            # every .md file in a folder
checkmarks -r ~/progress         # ...and in its subfolders
checkmarks a.md b.md notes/      # any mix of files and folders
fd -e md | checkmarks -          # read paths from stdin
checkmarks                       # $CHECKMARKS_DIR if set, else the current folder
```

In folders, files ending in `.md` or `.markdown` are read, sorted by path. With `-r`, folders whose names start with `.` (like `.git`) are skipped.

## File format

### Checklists

By default, checkmarks counts checkboxes:

```markdown
# My Todo List

- [ ] Buy groceries
- [x] Write blog post
  - [X] Nested items count too
1. [ ] Ordered lists work as well
```

- `[x]` and `[X]` are done; `[ ]` is pending.
- List items can start with `-`, `*`, `+`, `1.` or `1)`.
- Checkboxes inside fenced code blocks are ignored.

### Big things: break them down

checkmarks only counts checkboxes. To track a book, split it into chapters or page ranges, each one a task small enough to finish in a sitting:

```markdown
---
unit: chunks
---
# Dune

- [x] pp. 1–40
- [x] pp. 41–80
- [ ] pp. 81–120
- [ ] pp. 121–160
```

Supported frontmatter keys:

| Key     | Meaning                                  |
|---------|------------------------------------------|
| `unit`  | Label after the count (default `tasks`)  |
| `title` | Row title                                |

Other keys are ignored.

### Titles

The row title is the frontmatter `title`, else the first `# Heading`, else the filename.

## Output

On a terminal, checkmarks prints the aligned table shown above. Rows at 100% are green; set `NO_COLOR` or pass `--no-color` to turn colour off.

When output is piped, it switches to tab-separated rows with no header:

```
title  done  total  pct  unit  status  path
```

Use `--json` for a JSON array:

```bash
$ checkmarks --json dune.md
[
  {
    "title": "Dune",
    "done": 9,
    "total": 22,
    "pct": 40.9,
    "unit": "chapters",
    "status": "ok",
    "path": "dune.md"
  }
]
```

`status` is `ok`, `empty` (no checkboxes) or `error` (the file can't be read). Problems are reported on stderr, and the row is still shown.

Empty files found in folders are hidden; pass `--all` to show them. Files you name directly are always shown.

## Options

| Option                       | Description                                 |
|------------------------------|---------------------------------------------|
| `-r`, `--recursive`          | Descend into subfolders                     |
| `--all`                      | Show empty files found in folders           |
| `--format {pretty,tsv,json}` | Choose the output format                    |
| `--json`                     | Same as `--format json`                     |
| `--no-color`                 | Disable colour                              |
| `-v`, `--verbose`            | Also warn about files with no checkboxes    |

Exit code is `0` if at least one file has progress to show, `1` if none does, and `2` for usage errors.

## Upgrading from 0.2

- The `progress: N/M` frontmatter key (counter mode) is gone. Replace it with a checklist of chapters or page ranges.
- The `mode` column (TSV) and field (JSON) are removed.

## Upgrading from 0.1

- Output is now a table row per file instead of the old "📊 Progress for:" block.
- Python 3.11 or newer is required.
- Plain checklist files need no changes.

## Contributing

Feel free to submit issues or pull requests. This is a small tool, so contributions are always welcome.

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
