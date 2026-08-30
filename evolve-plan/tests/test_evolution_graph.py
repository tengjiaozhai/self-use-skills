import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "evolution_graph.py"
TODAY = date.today().isoformat()


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def node(
    node_id: str,
    slug: str,
    *,
    area: str = "auth",
    evolves_from: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    status: str = "adopted",
) -> tuple[str, str]:
    def links(values: tuple[str, ...]) -> str:
        if not values:
            return " []"
        return "\n" + "\n".join(f'  - "[[{value}]]"' for value in values)

    content = f"""---
id: {node_id}
date: {TODAY}
area: {area}
evolves_from:{links(evolves_from)}
depends_on:{links(depends_on)}
status: {status}
---

# {slug}

## 为什么变化

原因。

## 发生了什么

变化。

## 最终结果

结果。
"""
    return f"{node_id}-{slug}.md", content


def plan(revision: int, context: tuple[str, ...]) -> str:
    links = (
        "\n" + "\n".join(f'  - "[[{value}]]"' for value in context)
        if context
        else " []"
    )
    return f"""---
revision: {revision}
updated: {TODAY}
context:{links}
---

# Plan

## Goal

目标。

## Current

当前状态。

## Plan

1. 实施并验证。

## Progress

- [ ] **Current:** 实施。
"""


class EvolutionGraphCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "evolution").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_node(self, data: tuple[str, str]) -> Path:
        name, content = data
        path = self.root / "evolution" / name
        path.write_text(content)
        return path

    def test_inspect_returns_current_leaf_and_bounded_history(self) -> None:
        first = self.write_node(node("EV-001", "password-auth"))
        second = self.write_node(node("EV-002", "jwt-auth", evolves_from=(first.stem,)))
        third = self.write_node(
            node("EV-003", "oauth-auth", evolves_from=(second.stem,))
        )
        self.root.joinpath("PLAN.md").write_text(plan(3, (third.stem,)))

        result = run_cli("inspect", "--root", str(self.root), "--area", "auth")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["graph"]["valid"])
        self.assertEqual(payload["plan"]["revision"], 3)
        self.assertEqual(payload["graph"]["current_leaves"]["auth"], ["EV-003"])
        self.assertEqual(
            [item["id"] for item in payload["selection"]["nodes"]],
            ["EV-003", "EV-002", "EV-001"],
        )
        self.assertEqual(payload["graph"]["next_id"], "EV-004")
        self.assertEqual(payload["selection"]["omitted"], [])

    def test_validate_reports_missing_edge_target(self) -> None:
        self.write_node(node("EV-001", "oauth-auth", evolves_from=("EV-999-missing",)))

        result = run_cli("validate", "--root", str(self.root))

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertIn("missing target EV-999-missing", "\n".join(payload["errors"]))

    def test_validate_reports_evolution_cycle(self) -> None:
        self.write_node(node("EV-001", "first", evolves_from=("EV-002-second",)))
        self.write_node(node("EV-002", "second", evolves_from=("EV-001-first",)))

        result = run_cli("validate", "--root", str(self.root))

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertIn("evolves_from cycle", "\n".join(payload["errors"]))

    def test_optional_node_fields_use_runtime_defaults(self) -> None:
        name, content = node("EV-001", "password-auth")
        content = content.replace("depends_on: []\n", "").replace(
            "status: adopted\n", ""
        )
        self.write_node((name, content))

        result = run_cli("validate", "--root", str(self.root))

        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_leaves"]["auth"], ["EV-001"])

    def test_abandoned_branch_is_not_a_current_leaf(self) -> None:
        root_node = self.write_node(node("EV-001", "password-auth"))
        self.write_node(node("EV-002", "jwt-auth", evolves_from=(root_node.stem,)))
        self.write_node(
            node(
                "EV-003",
                "discarded-oauth",
                evolves_from=(root_node.stem,),
                status="abandoned",
            )
        )

        result = run_cli("validate", "--root", str(self.root))

        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_leaves"]["auth"], ["EV-002"])

    def test_inspect_adds_direct_design_dependency(self) -> None:
        session = self.write_node(node("EV-010", "session", area="session"))
        first = self.write_node(
            node("EV-001", "password-auth", depends_on=(session.stem,))
        )
        second = self.write_node(node("EV-002", "jwt-auth", evolves_from=(first.stem,)))
        self.root.joinpath("PLAN.md").write_text(plan(2, (second.stem,)))

        result = run_cli("inspect", "--root", str(self.root), "--area", "auth")

        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [item["id"] for item in payload["selection"]["nodes"]],
            ["EV-002", "EV-001", "EV-010"],
        )
        self.assertEqual(payload["graph"]["next_id"], "EV-011")

    def test_inspect_caps_context_and_reports_omitted_nodes(self) -> None:
        dependencies: list[str] = []
        for number in range(2, 14):
            dependency = self.write_node(
                node(f"EV-{number:03d}", f"dependency-{number}", area="shared")
            )
            dependencies.append(dependency.stem)
        seed = self.write_node(node("EV-001", "auth", depends_on=tuple(dependencies)))
        self.root.joinpath("PLAN.md").write_text(plan(1, (seed.stem,)))

        result = run_cli("inspect", "--root", str(self.root), "--area", "auth")

        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["selection"]["nodes"]), 12)
        self.assertEqual(payload["selection"]["omitted"], ["EV-002"])

    def test_apply_writes_plan_and_node_after_hash_guard(self) -> None:
        current = self.write_node(node("EV-001", "password-auth"))
        old_plan = plan(1, (current.stem,))
        plan_path = self.root / "PLAN.md"
        plan_path.write_text(old_plan)
        plan_path.chmod(0o640)

        inspected = json.loads(
            run_cli("inspect", "--root", str(self.root), "--area", "auth").stdout
        )
        staged = self.root / "stage"
        staged.mkdir()
        next_node = node("EV-002", "jwt-auth", evolves_from=(current.stem,))
        staged_node = staged / next_node[0]
        staged_node.write_text(next_node[1])
        staged_plan = staged / "PLAN.md"
        staged_plan.write_text(plan(2, (staged_node.stem,)))

        result = run_cli(
            "apply",
            "--root",
            str(self.root),
            "--plan-source",
            str(staged_plan),
            "--node-source",
            str(staged_node),
            "--expected-plan-sha",
            inspected["plan"]["sha256"],
            "--expected-graph-sha",
            inspected["graph"]["sha256"],
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "applied")
        self.assertEqual(payload["plan"]["revision"], 2)
        self.assertTrue(self.root.joinpath("evolution", staged_node.name).exists())
        self.assertEqual(
            hashlib.sha256(self.root.joinpath("PLAN.md").read_bytes()).hexdigest(),
            payload["plan"]["sha256"],
        )
        self.assertEqual(plan_path.stat().st_mode & 0o777, 0o640)

    def test_apply_rejects_stale_plan_without_writing(self) -> None:
        current = self.write_node(node("EV-001", "password-auth"))
        plan_path = self.root / "PLAN.md"
        plan_path.write_text(plan(1, (current.stem,)))
        inspected = json.loads(
            run_cli("inspect", "--root", str(self.root), "--area", "auth").stdout
        )
        plan_path.write_text(plan(7, (current.stem,)))

        staged_plan = self.root / "staged-plan.md"
        staged_plan.write_text(plan(2, (current.stem,)))
        result = run_cli(
            "apply",
            "--root",
            str(self.root),
            "--plan-source",
            str(staged_plan),
            "--expected-plan-sha",
            inspected["plan"]["sha256"],
            "--expected-graph-sha",
            inspected["graph"]["sha256"],
        )

        self.assertEqual(result.returncode, 3)
        self.assertEqual(plan_path.read_text(), plan(7, (current.stem,)))
        self.assertIn("plan hash changed", result.stdout)

    def test_apply_rejects_missing_plan_context_without_writing(self) -> None:
        current = self.write_node(node("EV-001", "password-auth"))
        plan_path = self.root / "PLAN.md"
        original = plan(1, (current.stem,))
        plan_path.write_text(original)
        inspected = json.loads(
            run_cli("inspect", "--root", str(self.root), "--area", "auth").stdout
        )
        staged_plan = self.root / "staged-plan.md"
        staged_plan.write_text(plan(2, ("EV-999-missing",)))

        result = run_cli(
            "apply",
            "--root",
            str(self.root),
            "--plan-source",
            str(staged_plan),
            "--expected-plan-sha",
            inspected["plan"]["sha256"],
            "--expected-graph-sha",
            inspected["graph"]["sha256"],
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(plan_path.read_text(), original)
        self.assertIn("context missing target EV-999-missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
