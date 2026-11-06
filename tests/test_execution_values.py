"""CT input boundaries and recursive execution prerequisites, not an input solver."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.workbench import Workbench, analyze_project
from autosar_trace_navigator.models import SourceRange, ValueProbe
from c_build import run_c99

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test/value_paths"


def guarded_workbench():
    workbench = Workbench()
    workbench.project = analyze_project(SAMPLE, include_paths=("value_paths.c", "value_paths.h"))
    function = workbench.project.functions_by_name["ValuePath_Consume"][0]
    branch = next(b for result in workbench.project.results for b in result.branches if b.function_id == function.id)
    workbench.start(function.id, branch.id, "값과 실행 조건 조사")
    workbench.set_variable_goal("pedal", "60", branch.location)
    return workbench


def follow_kind(workbench, kind, expression=None):
    candidate = next(c for c in workbench.value_candidates() if c.value_kind == kind
                     and (expression is None or c.label.endswith(expression)))
    workbench.follow(candidate, "값 공급 지점 확인")
    return candidate


class ExecutionValueTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)

    def test_no_literal_target_and_nested_calculation_operand_reaches_ct_global(self):
        workbench = guarded_workbench()
        self.assertNotIn(b"60", (SAMPLE / "value_paths.c").read_bytes())
        follow_kind(workbench, "rte_data")
        operand = follow_kind(workbench, "expression_operand", "ValuePath_RawInput")
        self.assertIn("expression_not_inverted", operand.uncertainty)
        terminal = follow_kind(workbench, "ct_global_input")
        self.assertIn("ct_accessibility_not_verified", terminal.uncertainty)
        self.assertIsNone(workbench.manager.current_step.probe)
        self.assertEqual(workbench.session.variable_goal.target_value, "60")

    def test_else_if_requires_prior_false_current_true_and_nested_true(self):
        workbench = guarded_workbench()
        follow_kind(workbench, "rte_data")
        row = follow_kind(workbench, "expression_operand", "ValuePath_RawInput")
        conditions = workbench.project.value_resolver.conditions(row.evidence)
        self.assertEqual([(r.expression, r.required_truth) for r in conditions], [
            ("(ValuePath_ModeInput == 0u)", False),
            ("(ValuePath_ModeInput == 2u)", True),
            ("(value_path_permit != 0u)", True),
        ])
        self.assertTrue(all("condition_satisfiability_not_proven" in r.uncertainty for r in conditions))

    def test_recursive_condition_investigations_preserve_original_and_alternative_tree(self):
        workbench = guarded_workbench()
        follow_kind(workbench, "rte_data")
        follow_kind(workbench, "expression_operand", "ValuePath_RawInput")
        calculation_step = workbench.manager.current_step
        target = workbench.session.target_branch
        permit = next(c for c in workbench.execution_candidates() if c.probe and c.probe.expression == "value_path_permit")
        workbench.follow(permit, "계산을 실행하려면 permit가 필요")
        self.assertFalse(any(c.value_kind == "ct_global_input" for c in workbench.value_candidates()))  # static.
        follow_kind(workbench, "constant", "1u")
        enable = next(c for c in workbench.execution_candidates() if c.probe and c.probe.expression == "ValuePath_EnableInput")
        workbench.follow(enable, "permit를 만드는 분기를 조사")
        terminal = follow_kind(workbench, "ct_global_input")
        self.assertTrue(any("ValuePath_EnableInput == 1u" in reason for reason in terminal.uncertainty))
        workbench.select(calculation_step.id)
        mode = next(c for c in workbench.execution_candidates() if c.probe and c.probe.expression == "ValuePath_ModeInput")
        workbench.follow(mode, "같은 계산의 다른 조건 조사")
        self.assertEqual(workbench.manager.current_step.parent_id, calculation_step.id)
        children = [s for s in workbench.session.steps if s.parent_id == calculation_step.id]
        self.assertEqual(len(children), 2)
        self.assertEqual(workbench.session.target_branch, target)
        self.assertEqual(workbench.session.variable_goal.variable, "pedal")
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "conditions.sqlite3"
            workbench.save(database)
            restored = Workbench()
            restored.restore(database, workbench.session.id)
            self.assertEqual(restored.session, workbench.session)

    def test_static_const_and_local_are_not_ct_global_inputs_but_extern_is_candidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "boundary.c"
            path.write_text("static int hidden; const int fixed=3; extern int exposed; extern int NotVariable(void);\n"
                            "int F(void) { int local=2; return hidden+fixed+local+exposed; }", encoding="utf-8")
            project = analyze_project(directory)
            function = project.functions_by_name["F"][0]
            data = dict(project.sources)[path]
            offset = data.index(b"return hidden")
            location = SourceRange(path, 2, 1, 2, 1, offset, offset)
            for name in ("hidden", "fixed", "local", "exposed", "NotVariable"):
                rows = project.value_resolver.sources(ValueProbe(function.id, name, location))
                self.assertEqual(any(row.kind == "ct_global_input" for row in rows), name == "exposed")

    def test_header_extern_candidate_keeps_header_visibility_uncertainty(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "use.c"
            path.write_text("int F(void) { return HeaderInput; }", encoding="utf-8")
            (Path(directory) / "input.h").write_text("extern unsigned HeaderInput;", encoding="utf-8")
            project = analyze_project(directory)
            function = project.functions[0]
            rows = project.value_resolver.sources(ValueProbe(function.id, "HeaderInput", function.body_location))
            boundary = next(r for r in rows if r.kind == "ct_global_input")
            self.assertIn("header_visibility_not_verified", boundary.uncertainty)

    def test_else_conditions_include_all_prior_arms_false_and_calls_not_variable_names(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "else.c"
            path.write_text("int F(int gate) { int value=0; if (Check(gate)) value=1; "
                            "else if (gate==2) value=2; else value=3; return value; }", encoding="utf-8")
            project = analyze_project(directory)
            function = project.functions[0]
            data = dict(project.sources)[path]
            offset = data.index(b"value=3")
            site = SourceRange(path, 1, offset + 1, 1, offset + 1, offset, offset)
            rows = project.value_resolver.conditions(site)
            self.assertEqual([r.required_truth for r in rows], [False, False])
            self.assertEqual({v.expression for row in rows for v in row.variables}, {"gate"})
            self.assertTrue(all(r.function_id == function.id for r in rows))

    def test_real_c_execution_checks_calculation_and_each_gate(self):
        output = run_c99(sorted(SAMPLE.glob("*.c")), include_dirs=(SAMPLE,))
        self.assertIn("PASS guarded value paths: 6 scenarios", output)
        print(output, end="")


class ExecutionGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Navigator(self.root, guarded_workbench())

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()

    def test_guard_preview_and_child_investigation_keep_goal_and_expose_ct_boundary(self):
        workbench = self.app.workbench
        follow_kind(workbench, "rte_data")
        self.app.refresh_trace()
        key = next(key for key, c in self.app.candidate_map.items()
                   if c.value_kind == "expression_operand" and c.probe.expression == "ValuePath_RawInput")
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.assertIn("value_path_permit != 0u", self.app.detail.get("1.0", "end"))
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="계산 위치"):
            self.app.follow(self.app.values)
        goal = self.app.goal.get()
        key = next(key for key, c in self.app.candidate_map.items()
                   if c.value_kind == "execution_condition" and c.probe.expression == "ValuePath_ModeInput")
        self.app.requirements.selection_set(key)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="계산의 mode 조건"):
            self.app.follow(self.app.requirements)
        self.assertEqual(self.app.goal.get(), goal)
        self.assertIn("하위 조사 조건:", self.app.context.get())
        self.assertTrue(any("CT 전역 제어 후보" in self.app.values.item(key, "values")[0]
                            for key in self.app.values.get_children()))
        self.assertTrue(all("1." in self.app.history.item(step.id, "values")[0]
                            for step in workbench.session.steps[1:]))

    def test_compact_layout_exposes_condition_tab_action(self):
        self.root.geometry("1100x760")
        self.root.deiconify()
        self.root.update()
        notebook = self.app.requirements.master.master.master
        notebook.select(self.app.requirements.master.master)
        self.root.update()
        button = next(b for b in self.app.buttons if b.cget("text") == "조건 변수 하위 조사")
        self.assertTrue(button.winfo_ismapped())
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), self.root.winfo_rooty() + self.root.winfo_height())

    def test_ct_boundary_explains_stop_and_restores_without_source_analysis(self):
        workbench = self.app.workbench
        follow_kind(workbench, "rte_data")
        follow_kind(workbench, "expression_operand", "ValuePath_RawInput")
        follow_kind(workbench, "ct_global_input")
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "boundary.sqlite3"
            workbench.save(database)
            restored = Workbench()
            restored.restore(database, workbench.session.id)
            self.app.workbench = restored
            self.app.refresh_trace()
            self.assertIn("CT 전역 후보에서 값 추적 중지", self.app.context.get())
            self.assertIn("실제 CT 접근성", self.app.detail.get("1.0", "end"))
            self.assertFalse(self.app.values.get_children())
            self.assertFalse(restored.dirty)
            self.assertIn("pedal → 60", self.app.goal.get())

    def test_long_alternative_history_keeps_current_row_visible_after_restore_and_back(self):
        workbench = self.app.workbench
        follow_kind(workbench, "rte_data")
        follow_kind(workbench, "expression_operand", "ValuePath_RawInput")
        parent = workbench.manager.current_step.id
        for index in range(18):
            workbench.select(parent)
            candidate = next(c for c in workbench.execution_candidates()
                             if c.probe and c.probe.expression == "ValuePath_ModeInput")
            workbench.follow(candidate, f"조건 조사 대안 {index}")
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "tree.sqlite3"
            workbench.save(database)
            workbench.restore(database, workbench.session.id)
            self.root.geometry("1100x760")
            self.root.deiconify()
            self.app.refresh_trace()
            self.root.update()
            current = workbench.session.current_step_id
            self.assertTrue(self.app.history.bbox(current))
            before = workbench.session
            self.app.history.selection_set(parent)
            self.app.preview_history()
            self.root.update()
            self.assertEqual(workbench.session, before)
            self.assertFalse(workbench.dirty)
            self.app.back()
            self.root.update()
            self.assertEqual(workbench.session.current_step_id, parent)
            self.assertTrue(self.app.history.bbox(parent))


if __name__ == "__main__":
    unittest.main()
