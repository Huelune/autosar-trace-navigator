"""Investigation state tests using parser outputs from synthetic AUTOSAR code."""

from dataclasses import replace
from pathlib import Path
import unittest

from autosar_trace_navigator.parser import parse_file
from autosar_trace_navigator.scanner import scan_sources
from autosar_trace_navigator.trace import TraceManager


ROOT = Path(__file__).resolve().parents[1]


def sample_manager() -> tuple[TraceManager, dict]:
    """Build an investigation at the sample's ASSIST branch."""
    results = [parse_file(s.path) for s in scan_sources(ROOT / "test", exclude_paths=("parser_cases",))]
    functions = {f.name: f for r in results for f in r.functions}
    target = next(b for r in results for b in r.branches if b.condition == "(mode == BRAKE_ASSIST)")
    return TraceManager.start(functions["BrakeControl_10ms"], target,
                              reason="ASSIST 분기의 성립 조건 조사"), functions


class TraceTests(unittest.TestCase):
    def test_six_steps_preserve_original_goal_and_reasons(self):
        manager, functions = sample_manager()
        target = manager.session.target_branch
        names = ("EvaluateBrakeMode", "IsAssistRequested", "IsSpeedEligible",
                 "GetValidatedSpeed", "DecodeSpeed", "ReadRawSpeed")
        for name in names:
            manager.follow(functions[name], reason=f"{name}의 입력 조건 확인", relation="call",
                           evidence=manager.current_step.function.body_location,
                           uncertainty=("unresolved_call_target",))
        self.assertEqual(len(manager.current_path), 7)
        self.assertEqual(manager.session.target_branch, target)
        self.assertEqual(target.location.start_line, 10)
        self.assertEqual([s.function.name for s in manager.current_path][1:], list(names))
        self.assertTrue(all(s.reason for s in manager.current_path))
        self.assertIn("unresolved_call_target", manager.current_step.uncertainty)

    def test_backtrack_new_path_preserves_previous_alternative(self):
        manager, functions = sample_manager()
        previous = manager.follow(functions["EvaluateBrakeMode"], reason="모드 계산 확인")
        manager.back()
        alternate = manager.follow(functions["SensorAcquisition_10ms"], reason="속도 공급자 조사",
                                   relation="rte_data", evidence=functions["ReadRawSpeed"].body_location)
        self.assertEqual(len(manager.session.steps), 3)
        self.assertEqual(len(manager.current_path), 2)
        self.assertEqual(manager.current_step, alternate)
        self.assertEqual(alternate.relation, "rte_data")
        manager.select(previous.id)
        self.assertEqual(manager.current_step, previous)

    def test_invalid_operations_leave_state_unchanged(self):
        manager, functions = sample_manager()
        before = manager.session
        for operation in (
            lambda: manager.back(), lambda: manager.select("missing"),
            lambda: manager.follow(functions["DecodeSpeed"], reason=" "),
            lambda: manager.follow(functions["DecodeSpeed"], reason="조사", relation="call"),
            lambda: manager.follow(functions["DecodeSpeed"], reason="조사", relation="root"),
        ):
            with self.assertRaises(ValueError):
                operation()
            self.assertEqual(manager.session, before)

    def test_wrong_target_and_invalid_restored_history_rejected(self):
        manager, functions = sample_manager()
        session = manager.session
        with self.assertRaises(ValueError):
            TraceManager.start(functions["DecodeSpeed"], session.target_branch, reason="목표")
        for changed in (
            replace(session, current_step_id="missing"),
            replace(session, steps=()),
            replace(session, steps=(session.steps[0], session.steps[0])),
            replace(session, steps=(replace(session.steps[0], parent_id="missing"),)),
        ):
            with self.assertRaises(ValueError):
                TraceManager(changed)

    def test_recursion_can_be_investigated_without_cycle_in_history(self):
        manager, functions = sample_manager()
        manager.follow(functions["BrakeControl_10ms"], reason="재귀 호출 가능성 조사")
        self.assertEqual(len(manager.current_path), 2)
        self.assertNotEqual(manager.current_path[0].id, manager.current_path[1].id)


if __name__ == "__main__":
    unittest.main()
