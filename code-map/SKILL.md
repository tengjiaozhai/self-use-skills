---
name: code-map
description: Maintain or use a repository-root CODEMAP.md that maps Git-tracked text files to concise responsibilities. Use when creating or updating a code map, checking whether it reflects file changes, locating relevant files for a task, or after an authorized change adds, removes, moves, or repurposes files. Do not use for symbol indexes, dependency graphs, or architecture history.
---

# Code Map

Maintain `CODEMAP.md` as a small navigation index. Code is the authority for current behavior; the map only answers what each included file is responsible for.

## Scope

Work from the root returned by `git rev-parse --show-toplevel`. Include Git-tracked, hand-maintained text files when their role helps an agent decide what to read. Tests, configuration, and documentation belong when their responsibility is not obvious from the path alone.

Leave out binaries, lockfiles, vendored code, caches, generated artifacts, and `CODEMAP.md` itself. Prefer a useful index over a directory-tree mirror.

Use one entry per file, grouped by directory:

```md
# Code Map

## src/auth

- [`src/auth/service.py`](src/auth/service.py) — Handles sign-in, token issuance, and session validation.
```

Keep each responsibility to one sentence. Describe the file's stable role, not its symbol inventory, implementation details, history, planned work, or architecture decisions.

## Choose a mode

### Query

Use the existing map to route a task to likely files. Search the map first, then open only the matched files needed to verify the answer. Treat conflicting source code as current truth. Query is read-only.

### Check

Assess freshness without editing. Compare map paths with `git ls-files`, `git status --short`, and staged and unstaged name-status diffs. Inspect affected files only far enough to decide whether a file was added, removed, moved, or given a different core responsibility.

Report stale or uncertain entries precisely. A clean working tree alone does not prove that every responsibility is current.

### Update

Write only when the user asks to create or update the map, or when an already-authorized code change adds, removes, moves, or repurposes files. A routine internal edit does not require a map change.

For the first map, start from `git ls-files` and inspect only the files needed to identify useful responsibilities. For an existing map, preserve accurate entries and limit edits to affected paths. Preserve unrelated user edits already present in `CODEMAP.md`.

Finish when every map path exists, every included file has one concise responsibility, affected stale entries are removed or corrected, and no excluded inventory has been added.
