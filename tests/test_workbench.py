"""Headless GUI state contracts through real parser, RTE and storage APIs."""

from pathlib import Path
import tempfile
import unittest

from autosar_trace_navigator.storage import TraceConflictError
from autosar_trace_navigator.workbench import Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]


def sample_workbench() -> Workbench:
    """Start at the virtual AUTOSAR target branch."""
    workbench = Workbench()
    workbench.project = analyze_project(ROOT / "test", include_paths=("include", "src", "support"))
    function = next(f for f in workbench.project.functions if f.name == "BrakeControl_10ms")
    branch = next(b for r in workbench.project.results for b in r.branches
                  if b.condition == "(mode == BRAKE_ASSIST)")
    workbench.start(function.id, branch.id, "ASSIST 조건 조사")
    return workbench


class WorkbenchTests(unittest.TestCase):
    def test_six_calls_then_rte_are_separate_candidates(self):
        workbench = sample_workbench()
        target = workbench.session.target_branch
        for name in ("EvaluateBrakeMode", "IsAssistRequested", "IsSpeedEligible",
                     "GetValidatedSpeed", "DecodeSpeed", "ReadRawSpeed"):
            candidate = next(c for c in workbench.candidates() if c.function and c.function.name == name)
            self.assertEqual(candidate.relation, "call")
            workbench.follow(candidate, f"{name} 조건 확인")
        rte = next(c for c in workbench.candidates() if c.relation == "rte_data")
        self.assertEqual(rte.label, "Speed_Raw")
        workbench.follow(rte, "속도 공급자 조사")
        self.assertEqual(workbench.manager.current_step.function.name, "SensorAcquisition_10ms")
        self.assertEqual(workbench.session.target_branch, target)
        self.assertEqual(len(workbench.manager.current_path), 8)

    def test_unresolved_and_stale_candidates_cannot_be_followed(self):
        workbench = sample_workbench()
        for name in ("EvaluateBrakeMode", "IsAssistRequested", "IsSpeedEligible",
                     "GetValidatedSpeed", "DecodeSpeed"):
            workbench.follow(next(c for c in workbench.candidates()
                                  if c.function and c.function.name == name), "호출 조건 확인")
        unresolved = next(c for c in workbench.candidates() if c.function is None)
        before = workbench.session
        with self.assertRaises(ValueError):
            workbench.follow(unresolved, "조사")
        self.assertEqual(workbench.session, before)
        candidate = next(c for c in workbench.candidates() if c.function)
        workbench.follow(candidate, "이동")
        with self.assertRaises(ValueError):
            workbench.follow(candidate, "이전 후보")

    def test_project_snapshot_preview_uses_exact_analyzed_bytes(self):
        workbench = sample_workbench()
        for path, data in workbench.project.sources:
            self.assertEqual(path.read_bytes(), data)
        before = workbench.session
        with self.assertRaises(FileNotFoundError):
            analyze_project(ROOT / "missing")
        self.assertEqual(workbench.session, before)

    def test_restore_save_conflict_and_failed_restore_keep_state(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            database = Path(directory) / "gui.sqlite3"
            first = sample_workbench()
            first.save(database)
            self.assertFalse(first.dirty)
            second = Workbench()
            second.restore(database, first.session.id)
            self.assertTrue(second.restored)
            self.assertFalse(second.candidates())  # No source analysis loaded.
            candidate = next(c for c in first.candidates() if c.function)
            first.follow(candidate, "조건 확인")
            first.save(database)
            old_revision = second.revision
            with self.assertRaises(TraceConflictError):
                second.save(database)
            self.assertEqual(second.revision, old_revision)
            before = second.session
            with self.assertRaises(KeyError):
                second.restore(database, "missing")
            self.assertEqual(second.session, before)

    def test_backtracking_history_and_invalid_start_preserve_goal(self):
        workbench = sample_workbench()
        root = workbench.session.current_step_id
        candidate = next(c for c in workbench.candidates() if c.function)
        workbench.follow(candidate, "mode 확인")
        workbench.back()
        self.assertEqual(workbench.session.current_step_id, root)
        self.assertEqual(len(workbench.session.steps), 2)
        before = workbench.session
        with self.assertRaises(ValueError):
            workbench.start("missing", "missing", "조사")
        self.assertEqual(workbench.session, before)


if __name__ == "__main__":
    unittest.main()
