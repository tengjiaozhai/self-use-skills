---
name: code-map
description: "Create or use repository navigation docs: a root AGENTS.md for task routing and CODEMAP.md for concise file responsibilities. Use when bootstrapping these docs, checking or updating a code map, locating relevant files, or after an authorized change adds, removes, moves, or repurposes files. Do not use for symbol indexes, dependency graphs, or architecture history."
---

# Code Map

Maintain `CODEMAP.md` as a small navigation index. Code is the authority for current behavior; the map only answers what each included file is responsible for. `AGENTS.md` routes tasks and records repository-wide operating rules without duplicating the map.

## Scope

Work from the root returned by `git rev-parse --show-toplevel`. Include Git-tracked, hand-maintained text files when their role helps an agent decide what to read. Tests, configuration, and documentation belong when their responsibility is not obvious from the path alone.

Leave out binaries, lockfiles, vendored code, caches, generated artifacts, and `CODEMAP.md` itself. Prefer a useful index over a directory-tree mirror.

Treat `PLAN.md` and `evolution/*.md` as evolve-plan's hand-maintained outputs and include them in the map when present. When evolve-plan calls this skill after an advance, prioritize entries for the files it just wrote.

Use one entry per file, grouped by directory. Keep each responsibility to one sentence. Describe the file's stable role, not its symbol inventory, implementation details, history, planned work, or architecture decisions.

## Choose a mode

### Bootstrap

Use when the user asks to create repository navigation docs. Read [references/AGENTS.md](references/AGENTS.md) for the task-routing shape and [references/CODEMAP.md](references/CODEMAP.md) for the file-map shape. Adapt both to the target repository; the examples are not content to copy verbatim.

Create root `AGENTS.md` and `CODEMAP.md` only within the user's authorized scope. If either already exists, preserve its valid content and change only what the request requires.

### Query

Use the existing map to route a task to likely files. Search the map first, then open only the matched files needed to verify the answer. Treat conflicting source code as current truth. Query is read-only.

### Check

Assess freshness without editing. Compare map paths with `git ls-files`, `git status --short`, and staged and unstaged name-status diffs. Inspect affected files only far enough to decide whether a file was added, removed, moved, or given a different core responsibility.

Report stale or uncertain entries precisely. A clean working tree alone does not prove that every responsibility is current.

### Update

Write only when the user asks to create or update the map, or when an already-authorized code change adds, removes, moves, or repurposes files. A routine internal edit does not require a map change.

For the first map, start from `git ls-files` and inspect only the files needed to identify useful responsibilities. For an existing map, preserve accurate entries and limit edits to affected paths. Preserve unrelated user edits already present in `CODEMAP.md`.

Finish when every map path exists, every included file has one concise responsibility, affected stale entries are removed or corrected, and no excluded inventory has been added.
