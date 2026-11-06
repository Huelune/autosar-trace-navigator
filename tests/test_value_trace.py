"""Variable objective, explicit selected locations and backward-compatible snapshots."""

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.workbench import Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]


def pedal_workbench() -> Workbench:
    workbench = Workbench()
    workbench.project = analyze_project(ROOT / "test", include_paths=("include", "src", "support"))
    function = workbench.project.functions_by_name["IsAssistRequested"][0]
    target = next(b for r in workbench.project.results for b in r.branches
                  if b.function_id == function.id and "pedal >= 60u" in (b.condition or ""))
    workbench.start(function.id, target.id, "pedal 입력을 60으로 준비")
    workbench.set_variable_goal("pedal", "60", target.location)
    return workbench


class ValueTraceTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "values.sqlite3"

    def test_input_chain_goal_and_selected_lines_survive_restore(self):
        workbench = pedal_workbench()
        goal = workbench.session.variable_goal
        original_branch = workbench.session.target_branch
        for kind in ("rte_data", "return_value", "return", "global_write"):
            candidate = next(c for c in workbench.value_candidates() if c.value_kind == kind)
            workbench.follow(candidate, f"{kind} 공급 경로 확인")
            self.assertEqual(workbench.session.variable_goal, goal)
            self.assertEqual(workbench.manager.current_step.selected_location, candidate.selected_location)
        terminal = next(c for c in workbench.value_candidates() if c.value_kind == "constant" and c.label.endswith("60u"))
        workbench.follow(terminal, "60u 테스트 입력 위치 확인")
        self.assertIsNone(workbench.manager.current_step.probe)
        self.assertFalse(workbench.value_candidates())
        self.assertEqual(workbench.manager.current_step.selected_location, terminal.evidence)
        workbench.save(self.database)
        restored = Workbench()
        restored.restore(self.database, workbench.session.id)
        self.assertEqual(restored.session, workbench.session)
        restored.select(restored.session.steps[0].id)
        self.assertEqual(restored.manager.current_step.selected_location, original_branch.location)
        self.assertEqual(restored.session.variable_goal.variable, "pedal")
        self.assertEqual(restored.session.variable_goal.target_value, "60")

    def test_goal_fixed_but_current_probe_can_change(self):
        workbench = pedal_workbench()
        goal = workbench.session.variable_goal
        workbench.inspect_variable("eligible", goal.location)
        self.assertEqual(workbench.session.variable_goal, goal)
        self.assertEqual(workbench.manager.current_step.probe.expression, "eligible")
        before = workbench.session
        with self.assertRaises(ValueError):
            workbench.set_variable_goal("pedal", "70", goal.location)
        self.assertEqual(workbench.session, before)

    def test_invalid_goal_or_selected_file_does_not_mutate_history(self):
        workbench = pedal_workbench()
        before = workbench.session
        location = before.variable_goal.location
        for operation in (
            lambda: workbench.inspect_variable("object.pedal", location),
            lambda: workbench.record_location(replace(location, path=ROOT / "other.c")),
            lambda: workbench.record_location(replace(location, start_byte=99999, end_byte=99999)),
        ):
            with self.assertRaises(ValueError):
                operation()
            self.assertEqual(workbench.session, before)

    def test_record_location_keeps_goal_and_marks_save_dirty(self):
        workbench = pedal_workbench()
        workbench.save(self.database)
        goal = workbench.session.variable_goal
        workbench.record_location(workbench.manager.current_step.function.location)
        self.assertTrue(workbench.dirty)
        self.assertEqual(workbench.session.variable_goal, goal)
        self.assertEqual(workbench.manager.current_step.selected_location,
                         workbench.manager.current_step.function.location)

    def test_legacy_json_without_value_or_location_fields_restores(self):
        workbench = pedal_workbench()
        workbench.save(self.database)
        connection = sqlite3.connect(self.database)
        try:
            data = json.loads(connection.execute("SELECT payload FROM trace_sessions").fetchone()[0])
            data.pop("format_version")
            data.pop("variable_goal")
            for step in data["steps"]:
                step.pop("selected_location")
                step.pop("probe")
            connection.execute("UPDATE trace_sessions SET payload=?", (json.dumps(data),))
            connection.commit()
        finally:
            connection.close()
        restored = Workbench()
        restored.restore(self.database, workbench.session.id)
        self.assertIsNone(restored.session.variable_goal)
        self.assertIsNone(restored.manager.current_step.selected_location)
        self.assertEqual(restored.session.target_branch, workbench.session.target_branch)

    def test_unsupported_snapshot_format_is_rejected(self):
        workbench = pedal_workbench()
        workbench.save(self.database)
        connection = sqlite3.connect(self.database)
        try:
            data = json.loads(connection.execute("SELECT payload FROM trace_sessions").fetchone()[0])
            data["format_version"] = 99
            connection.execute("UPDATE trace_sessions SET payload=?", (json.dumps(data),))
            connection.commit()
        finally:
            connection.close()
        with TraceStore(self.database) as store, self.assertRaises(ValueError):
            store.load(workbench.session.id)


if __name__ == "__main__":
    unittest.main()
