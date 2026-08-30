#!/usr/bin/env python3
"""Deterministic Evolution Graph inspection, validation, and guarded writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


NODE_FIELDS = {
    "id",
    "date",
    "area",
    "evolves_from",
    "depends_on",
    "status",
}
PLAN_FIELDS = {"revision", "updated", "context"}
REQUIRED_NODE_FIELDS = {"id", "date", "area", "evolves_from"}
REQUIRED_PLAN_FIELDS = {"revision", "updated", "context"}
REQUIRED_NODE_H2 = ["为什么变化", "发生了什么", "最终结果"]
REQUIRED_PLAN_H2 = ["Goal", "Current", "Plan", "Progress"]
AREA_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_RE = re.compile(r"^EV-(\d{3,})$")
FILE_RE = re.compile(r"^(EV-\d{3,})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
KEY_RE = re.compile(r"^([a-z_]+):(.*)$")
LINK_RE = re.compile(r"^\[\[([^\[\]]+)\]\]$")
MAX_EVOLVES_HOPS = 3
MAX_NODES = 12
MISSING_SHA = "missing"


class ContractError(Exception):
    """Raised when an input violates the runtime contract."""


@dataclass(frozen=True)
class Document:
    path: Path
    fields: dict[str, Any]
    body: str


@dataclass(frozen=True)
class Node:
    path: Path
    stem: str
    id: str
    number: int
    date: str
    area: str
    evolves_from: tuple[str, ...]
    depends_on: tuple[str, ...]
    status: str
    title: str

    def summary(self, root: Path) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": str(self.path.relative_to(root)),
            "stem": self.stem,
            "date": self.date,
            "area": self.area,
            "status": self.status,
            "title": self.title,
        }


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(code)


def sha256_file(path: Path) -> str:
    if not path.exists():
        return MISSING_SHA
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_sha(evolution_dir: Path) -> str:
    digest = hashlib.sha256()
    if evolution_dir.exists():
        for path in sorted(evolution_dir.glob("*.md"), key=lambda item: item.name):
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def parse_scalar(raw: str, *, path: Path, line_number: int) -> Any:
    value = raw.strip()
    if value == "[]":
        return []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if re.fullmatch(r"\d+", value):
        return int(value)
    if value:
        return value
    raise ContractError(f"{path}:{line_number}: missing scalar value")


def parse_frontmatter(path: Path) -> Document:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path}: not valid UTF-8") from exc
    lines = raw.splitlines()
    if not lines or lines[0] != "---":
        raise ContractError(f"{path}: missing opening YAML fence")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ContractError(f"{path}: missing closing YAML fence") from exc

    fields: dict[str, Any] = {}
    index = 1
    while index < closing:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        match = KEY_RE.fullmatch(line)
        if not match:
            raise ContractError(f"{path}:{index + 1}: unsupported YAML syntax")
        key, remainder = match.groups()
        if key in fields:
            raise ContractError(f"{path}:{index + 1}: duplicate field {key}")
        if remainder.strip():
            fields[key] = parse_scalar(remainder, path=path, line_number=index + 1)
            index += 1
            continue

        values: list[str] = []
        index += 1
        while index < closing and lines[index].startswith("  - "):
            item = parse_scalar(lines[index][4:], path=path, line_number=index + 1)
            if not isinstance(item, str):
                raise ContractError(f"{path}:{index + 1}: list items must be strings")
            values.append(item)
            index += 1
        fields[key] = values

    body = "\n".join(lines[closing + 1 :]).strip() + "\n"
    return Document(path=path, fields=fields, body=body)


def parse_links(
    value: Any, *, field: str, path: Path, errors: list[str]
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        errors.append(f"{path}: {field} must be a list")
        return ()
    targets: list[str] = []
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{path}: {field} items must be strings")
            continue
        match = LINK_RE.fullmatch(item)
        if not match:
            errors.append(f"{path}: {field} item {item!r} is not a Wikilink")
            continue
        targets.append(match.group(1))
    return tuple(targets)


def heading_values(body: str, level: int) -> list[str]:
    prefix = "#" * level + " "
    return [
        line[len(prefix) :].strip()
        for line in body.splitlines()
        if line.startswith(prefix) and not line.startswith(prefix + "#")
    ]


def load_nodes(evolution_dir: Path) -> tuple[list[Node], list[str], list[str]]:
    nodes: list[Node] = []
    errors: list[str] = []
    warnings: list[str] = []
    if not evolution_dir.exists():
        return nodes, errors, warnings
    if not evolution_dir.is_dir():
        return nodes, [f"{evolution_dir}: must be a directory"], warnings

    for path in sorted(evolution_dir.glob("*.md"), key=lambda item: item.name):
        try:
            doc = parse_frontmatter(path)
        except ContractError as exc:
            errors.append(str(exc))
            continue
        unknown = sorted(set(doc.fields) - NODE_FIELDS)
        missing = sorted(REQUIRED_NODE_FIELDS - set(doc.fields))
        if unknown:
            errors.append(f"{path}: unknown fields {', '.join(unknown)}")
        if missing:
            errors.append(f"{path}: missing fields {', '.join(missing)}")

        node_id = doc.fields.get("id")
        file_match = FILE_RE.fullmatch(path.name)
        id_match = ID_RE.fullmatch(node_id) if isinstance(node_id, str) else None
        if not id_match:
            errors.append(f"{path}: id must match EV-<three-or-more-digits>")
            number = -1
        else:
            number = int(id_match.group(1))
        if not file_match:
            errors.append(f"{path}: filename must be EV-NNN-short-kebab-slug.md")
        elif node_id != file_match.group(1):
            errors.append(f"{path}: id does not match filename prefix")

        node_date = doc.fields.get("date")
        if not isinstance(node_date, str):
            errors.append(f"{path}: date must be YYYY-MM-DD")
        else:
            try:
                date.fromisoformat(node_date)
            except ValueError:
                errors.append(f"{path}: date must be YYYY-MM-DD")

        area = doc.fields.get("area")
        if not isinstance(area, str) or not AREA_RE.fullmatch(area):
            errors.append(f"{path}: area must be lowercase kebab-case")

        status = doc.fields.get("status", "adopted")
        if status not in {"adopted", "abandoned"}:
            errors.append(f"{path}: status must be adopted or abandoned")

        evolves_from = parse_links(
            doc.fields.get("evolves_from"),
            field="evolves_from",
            path=path,
            errors=errors,
        )
        depends_on = parse_links(
            doc.fields.get("depends_on", []),
            field="depends_on",
            path=path,
            errors=errors,
        )
        h1 = heading_values(doc.body, 1)
        h2 = heading_values(doc.body, 2)
        if len(h1) != 1:
            errors.append(f"{path}: body must contain exactly one H1")
        if h2 != REQUIRED_NODE_H2:
            errors.append(f"{path}: H2 headings must be {', '.join(REQUIRED_NODE_H2)}")

        if (
            isinstance(node_id, str)
            and id_match
            and isinstance(node_date, str)
            and isinstance(area, str)
            and AREA_RE.fullmatch(area)
            and status in {"adopted", "abandoned"}
        ):
            nodes.append(
                Node(
                    path=path,
                    stem=path.stem,
                    id=node_id,
                    number=number,
                    date=node_date,
                    area=area,
                    evolves_from=evolves_from,
                    depends_on=depends_on,
                    status=status,
                    title=h1[0] if len(h1) == 1 else path.stem,
                )
            )

    stems = {node.stem for node in nodes}
    ids: dict[str, list[Path]] = {}
    for node in nodes:
        ids.setdefault(node.id, []).append(node.path)
        for field, targets in (
            ("evolves_from", node.evolves_from),
            ("depends_on", node.depends_on),
        ):
            for target in targets:
                if target == node.stem:
                    errors.append(f"{node.path}: {field} cannot reference itself")
                elif target not in stems:
                    errors.append(f"{node.path}: {field} missing target {target}")
    for node_id, paths in ids.items():
        if len(paths) > 1:
            errors.append(
                f"duplicate id {node_id}: " + ", ".join(str(path) for path in paths)
            )

    cycle = find_cycle({node.stem: node.evolves_from for node in nodes})
    if cycle:
        errors.append("evolves_from cycle: " + " -> ".join(cycle))
    dependency_cycle = find_cycle({node.stem: node.depends_on for node in nodes})
    if dependency_cycle:
        warnings.append("depends_on cycle: " + " -> ".join(dependency_cycle))
    return nodes, errors, warnings


def find_cycle(edges: dict[str, Iterable[str]]) -> list[str]:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(stem: str) -> list[str]:
        state[stem] = 1
        stack.append(stem)
        for target in edges.get(stem, ()):
            if target not in edges:
                continue
            if state.get(target, 0) == 0:
                found = visit(target)
                if found:
                    return found
            elif state.get(target) == 1:
                start = stack.index(target)
                return stack[start:] + [target]
        stack.pop()
        state[stem] = 2
        return []

    for stem in sorted(edges):
        if state.get(stem, 0) == 0:
            found = visit(stem)
            if found:
                return found
    return []


def current_leaves(nodes: list[Node]) -> dict[str, list[Node]]:
    adopted = [node for node in nodes if node.status == "adopted"]
    evolved_in_area: set[str] = set()
    by_stem = {node.stem: node for node in adopted}
    for child in adopted:
        for target in child.evolves_from:
            parent = by_stem.get(target)
            if parent and parent.area == child.area:
                evolved_in_area.add(parent.stem)
    leaves: dict[str, list[Node]] = {}
    for node in adopted:
        if node.stem not in evolved_in_area:
            leaves.setdefault(node.area, []).append(node)
    for area in leaves:
        leaves[area].sort(key=node_sort_key)
    return dict(sorted(leaves.items()))


def node_sort_key(node: Node) -> tuple[str, int]:
    return (node.date, node.number)


def next_id(nodes: list[Node]) -> str:
    number = max((node.number for node in nodes), default=0) + 1
    return f"EV-{number:03d}"


def validate_graph(root: Path) -> dict[str, Any]:
    evolution_dir = root / "evolution"
    nodes, errors, warnings = load_nodes(evolution_dir)
    leaves = current_leaves(nodes)
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "sha256": graph_sha(evolution_dir),
        "node_count": len(nodes),
        "next_id": next_id(nodes),
        "current_leaves": {
            area: [node.id for node in area_nodes]
            for area, area_nodes in leaves.items()
        },
        "_nodes": nodes,
        "_leaves": leaves,
    }


def validate_plan(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "sha256": MISSING_SHA,
            "revision": 0,
            "updated": None,
            "context": [],
        }, []
    errors: list[str] = []
    try:
        doc = parse_frontmatter(path)
    except ContractError as exc:
        return {
            "exists": True,
            "path": str(path),
            "sha256": sha256_file(path),
            "revision": None,
            "updated": None,
            "context": [],
        }, [str(exc)]

    unknown = sorted(set(doc.fields) - PLAN_FIELDS)
    missing = sorted(REQUIRED_PLAN_FIELDS - set(doc.fields))
    if unknown:
        errors.append(f"{path}: unknown fields {', '.join(unknown)}")
    if missing:
        errors.append(f"{path}: missing fields {', '.join(missing)}")
    revision = doc.fields.get("revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append(f"{path}: revision must be a positive integer")
    updated = doc.fields.get("updated")
    if not isinstance(updated, str):
        errors.append(f"{path}: updated must be YYYY-MM-DD")
    else:
        try:
            date.fromisoformat(updated)
        except ValueError:
            errors.append(f"{path}: updated must be YYYY-MM-DD")
    context = parse_links(
        doc.fields.get("context"), field="context", path=path, errors=errors
    )
    h1 = heading_values(doc.body, 1)
    h2 = heading_values(doc.body, 2)
    if h1 != ["Plan"]:
        errors.append(f"{path}: body must contain exactly one '# Plan'")
    if h2 != REQUIRED_PLAN_H2:
        errors.append(f"{path}: H2 headings must be {', '.join(REQUIRED_PLAN_H2)}")
    return {
        "exists": True,
        "path": str(path),
        "sha256": sha256_file(path),
        "revision": revision,
        "updated": updated,
        "context": list(context),
    }, errors


def select_nodes(
    nodes: list[Node],
    leaves: dict[str, list[Node]],
    plan_context: list[str],
    areas: list[str],
) -> tuple[list[Node], list[Node], list[str]]:
    by_stem = {node.stem: node for node in nodes}
    leaf_stems = {node.stem for area_nodes in leaves.values() for node in area_nodes}
    requested = set(areas)
    seeds: list[Node] = []
    for stem in plan_context:
        node = by_stem.get(stem)
        if (
            node
            and node.stem in leaf_stems
            and (not requested or node.area in requested)
        ):
            seeds.append(node)
    for area in areas:
        seeds.extend(leaves.get(area, []))
    if not areas and not seeds:
        for area_nodes in leaves.values():
            seeds.extend(area_nodes)
    seeds = stable_unique(sorted(seeds, key=node_sort_key, reverse=True))
    if len(seeds) > MAX_NODES:
        raise ContractError(f"seed count {len(seeds)} exceeds max_nodes {MAX_NODES}")

    selected: list[Node] = list(seeds)
    ancestor_distance: dict[str, int] = {}
    frontier = [(seed, 0) for seed in seeds]
    while frontier:
        current, distance = frontier.pop(0)
        if distance >= MAX_EVOLVES_HOPS:
            continue
        for stem in current.evolves_from:
            target = by_stem.get(stem)
            if not target:
                continue
            new_distance = distance + 1
            old_distance = ancestor_distance.get(stem)
            if old_distance is None or new_distance < old_distance:
                ancestor_distance[stem] = new_distance
                frontier.append((target, new_distance))

    near = sorted(
        (
            by_stem[stem]
            for stem, distance in ancestor_distance.items()
            if distance == 1
        ),
        key=node_sort_key,
        reverse=True,
    )
    far = sorted(
        (by_stem[stem] for stem, distance in ancestor_distance.items() if distance > 1),
        key=node_sort_key,
        reverse=True,
    )
    seed_dependencies = dependency_nodes(seeds, by_stem)
    history_nodes = near + far
    history_dependencies = dependency_nodes(history_nodes, by_stem)
    ordered = stable_unique(
        selected + near + seed_dependencies + history_dependencies + far
    )
    kept = ordered[:MAX_NODES]
    omitted = [node.id for node in ordered[MAX_NODES:]]
    return seeds, kept, omitted


def dependency_nodes(source_nodes: list[Node], by_stem: dict[str, Node]) -> list[Node]:
    dependencies: list[Node] = []
    for source in source_nodes:
        for stem in source.depends_on:
            target = by_stem.get(stem)
            if target:
                dependencies.append(target)
    return stable_unique(sorted(dependencies, key=node_sort_key, reverse=True))


def stable_unique(nodes: Iterable[Node]) -> list[Node]:
    seen: set[str] = set()
    result: list[Node] = []
    for node in nodes:
        if node.stem not in seen:
            seen.add(node.stem)
            result.append(node)
    return result


def public_graph(graph: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in graph.items() if not key.startswith("_")}


def inspect_payload(root: Path, areas: list[str]) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    graph = validate_graph(root)
    plan, plan_errors = validate_plan(root / "PLAN.md")
    graph["errors"].extend(plan_errors)
    graph["errors"] = sorted(set(graph["errors"]))
    graph["valid"] = not graph["errors"]
    payload: dict[str, Any] = {
        "root": str(root),
        "plan": plan,
        "graph": public_graph(graph),
        "selection": {"areas": areas, "seeds": [], "nodes": [], "omitted": []},
    }
    if not graph["valid"]:
        return payload, 2
    try:
        seeds, selected, omitted = select_nodes(
            graph["_nodes"],
            graph["_leaves"],
            plan["context"],
            areas,
        )
    except ContractError as exc:
        payload["selection"]["error"] = str(exc)
        return payload, 4
    payload["selection"] = {
        "areas": areas,
        "seeds": [node.summary(root) for node in seeds],
        "nodes": [node.summary(root) for node in selected],
        "omitted": omitted,
    }
    return payload, 0


def copy_combined_graph(
    source_dir: Path, staged_dir: Path, node_sources: list[Path]
) -> None:
    staged_dir.mkdir(parents=True)
    if source_dir.exists():
        for path in source_dir.glob("*.md"):
            shutil.copy2(path, staged_dir / path.name)
    for source in node_sources:
        if not source.is_file():
            raise ContractError(f"node source does not exist: {source}")
        if not FILE_RE.fullmatch(source.name):
            raise ContractError(
                f"node source filename must be EV-NNN-short-kebab-slug.md: {source}"
            )
        destination = staged_dir / source.name
        if destination.exists():
            raise ContractError(f"node destination already exists: {source.name}")
        shutil.copy2(source, destination)


def validate_plan_context(plan: dict[str, Any], nodes: list[Node]) -> list[str]:
    stems = {node.stem for node in nodes}
    return [
        f"PLAN.md: context missing target {stem}"
        for stem in plan["context"]
        if stem not in stems
    ]


def atomic_replace(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = (
        destination.stat().st_mode if destination.exists() else source.stat().st_mode
    ) & 0o777
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def restore(
    plan_path: Path,
    old_plan: bytes | None,
    old_plan_mode: int | None,
    created_nodes: list[Path],
) -> None:
    for path in created_nodes:
        if path.exists():
            path.unlink()
    if old_plan is None:
        if plan_path.exists():
            plan_path.unlink()
    else:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{plan_path.name}.restore.", dir=plan_path.parent
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                if old_plan_mode is not None:
                    os.fchmod(handle.fileno(), old_plan_mode)
                handle.write(old_plan)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, plan_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()


def apply_changes(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    plan_path = root / "PLAN.md"
    evolution_dir = root / "evolution"
    actual_plan_sha = sha256_file(plan_path)
    actual_graph_sha = graph_sha(evolution_dir)
    stale: list[str] = []
    if actual_plan_sha != args.expected_plan_sha:
        stale.append("plan hash changed")
    if actual_graph_sha != args.expected_graph_sha:
        stale.append("graph hash changed")
    if stale:
        emit({"status": "blocked", "errors": stale}, 3)

    current_graph = validate_graph(root)
    current_plan, current_plan_errors = validate_plan(plan_path)
    pre_errors = current_graph["errors"] + current_plan_errors
    if pre_errors:
        emit({"status": "blocked", "errors": sorted(set(pre_errors))}, 2)

    plan_source = Path(args.plan_source).resolve()
    if not plan_source.is_file():
        emit(
            {"status": "blocked", "errors": [f"missing plan source {plan_source}"]},
            4,
        )
    staged_plan, staged_plan_errors = validate_plan(plan_source)
    if not staged_plan["exists"]:
        staged_plan_errors.append(f"{plan_source}: staged Plan is missing")
    expected_revision = current_plan["revision"] + 1 if current_plan["exists"] else 1
    if staged_plan["revision"] != expected_revision:
        staged_plan_errors.append(
            f"{plan_source}: revision must be {expected_revision}"
        )
    if staged_plan["updated"] != date.today().isoformat():
        staged_plan_errors.append(f"{plan_source}: updated must be today's local date")
    if plan_path.exists() and plan_source.read_bytes() == plan_path.read_bytes():
        staged_plan_errors.append(f"{plan_source}: effective Plan change is required")

    node_sources = [Path(value).resolve() for value in args.node_source]
    with tempfile.TemporaryDirectory(prefix="evolve-plan-validate.") as temp:
        staged_root = Path(temp)
        staged_evolution = staged_root / "evolution"
        try:
            copy_combined_graph(evolution_dir, staged_evolution, node_sources)
        except ContractError as exc:
            staged_plan_errors.append(str(exc))
        staged_graph = validate_graph(staged_root)
        staged_plan_errors.extend(staged_graph["errors"])
        staged_plan_errors.extend(
            validate_plan_context(staged_plan, staged_graph["_nodes"])
        )
        if staged_plan_errors:
            emit(
                {
                    "status": "blocked",
                    "errors": sorted(set(staged_plan_errors)),
                },
                2,
            )

    old_plan = plan_path.read_bytes() if plan_path.exists() else None
    old_plan_mode = plan_path.stat().st_mode & 0o777 if plan_path.exists() else None
    created_nodes: list[Path] = []
    try:
        evolution_dir.mkdir(parents=True, exist_ok=True)
        for source in node_sources:
            destination = evolution_dir / source.name
            atomic_replace(source, destination)
            created_nodes.append(destination)
        atomic_replace(plan_source, plan_path)

        post_graph = validate_graph(root)
        post_plan, post_plan_errors = validate_plan(plan_path)
        post_errors = (
            post_graph["errors"]
            + post_plan_errors
            + validate_plan_context(post_plan, post_graph["_nodes"])
        )
        if post_errors:
            raise ContractError("; ".join(sorted(set(post_errors))))
    except Exception as exc:
        restore(plan_path, old_plan, old_plan_mode, created_nodes)
        emit(
            {
                "status": "blocked",
                "errors": [f"write rolled back: {exc}"],
            },
            2,
        )

    payload, code = inspect_payload(root, [])
    payload.update(
        {
            "status": "applied",
            "modified": [
                "PLAN.md",
                *[f"evolution/{source.name}" for source in node_sources],
            ],
        }
    )
    emit(payload, code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and maintain an Evolution Graph."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--root", required=True)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--root", required=True)
    inspect.add_argument("--area", action="append", default=[])

    identifier = subparsers.add_parser("next-id")
    identifier.add_argument("--root", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--root", required=True)
    apply_parser.add_argument("--plan-source", required=True)
    apply_parser.add_argument("--node-source", action="append", default=[])
    apply_parser.add_argument("--expected-plan-sha", required=True)
    apply_parser.add_argument("--expected-graph-sha", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    if args.command == "validate":
        graph = validate_graph(root)
        code = 0 if graph["valid"] else 2
        emit(public_graph(graph), code)
    if args.command == "inspect":
        payload, code = inspect_payload(root, args.area)
        emit(payload, code)
    if args.command == "next-id":
        graph = validate_graph(root)
        if not graph["valid"]:
            emit(public_graph(graph), 2)
        emit({"next_id": graph["next_id"], "graph_sha256": graph["sha256"]})
    if args.command == "apply":
        apply_changes(args)


if __name__ == "__main__":
    try:
        main()
    except ContractError as exc:
        emit({"status": "blocked", "errors": [str(exc)]}, 4)
