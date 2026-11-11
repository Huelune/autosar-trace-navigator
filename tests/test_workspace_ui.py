"""Condition selection and independent source/comparison views, using actual Tk."""

from pathlib import Path
import tempfile
import gc
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.workbench import Workbench, analyze_project
from test_value_trace import pedal_workbench


ROOT = Path(__file__).resolve().parents[1]


class ConditionInputTests(unittest.TestCase):
    def test_members_pointers_arrays_and_callees_are_not_plain_variable_names(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "members.c"
            path.write_text("int F(void) { if (b.a > 0 && p->a > 0 && table[i] > 0 && Check(gate)) return 1; return 0; }",
                            encoding="utf-8")
            project = analyze_project(directory)
            inputs = project.value_resolver.branch_inputs(project.results[0].branches[0].id)
            self.assertEqual([(item.expression, item.supported) for item in inputs],
                             [("b.a", True), ("p->a", True), ("table[i]", False), ("gate", True)])


class WorkspaceUiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        workbench = pedal_workbench()
        workbench.start(workbench.session.target_function.id, workbench.session.target_branch.id, "다중 변수 분기 조사")
        self.app = Navigator(self.root, workbench)

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()
        del self.app, self.root
        gc.collect()  # finalize Tk objects on this thread, not in a later worker thread's GC

    def test_multiple_condition_variables_require_choice_and_use_the_selected_identifier_site(self):
        self.assertEqual(self.app.variable_entry["values"], ("eligible", "pedal"))
        self.assertEqual(self.app.variable.get(), "")
        self.assertIn("여러 개", self.app.input_help.get())
        before = self.app.workbench.session
        self.app.variable.set("pedal")
        self.app.choose_branch_input()
        site = self.app.picked_location
        data = dict(self.app.workbench.project.sources)[site.path]
        self.assertEqual(data[site.start_byte:site.end_byte], b"pedal")
        self.assertEqual(self.app.source.get(*self.app.source.tag_ranges("tracked_value")), "pedal")
        self.assertEqual(self.app.workbench.session, before)
        self.app.target_value.set("60")
        self.app.set_variable_goal()
        self.assertEqual(self.app.workbench.session.variable_goal.location, site)
        self.assertEqual(self.app.candidates_notebook.index("current"), 2)
        self.root.update_idletasks()
        self.assertFalse(self.app.goal_controls.winfo_manager())

    def test_preview_and_current_source_are_separate_and_simultaneously_visible(self):
        self.root.geometry("1100x760")
        self.root.deiconify()
        self.root.update()
        before = self.app.source.get("1.0", "end")
        selection = self.app.picked_location
        candidate = next(k for k, c in self.app.candidate_map.items()
                         if c.function and c.function.name == "IsSpeedEligible")
        self.app.calls.selection_set(candidate)
        self.app.preview_candidate(self.app.calls)
        self.root.update()
        self.assertEqual(self.app.source.get("1.0", "end"), before)
        self.assertEqual(self.app.picked_location, selection)
        self.assertIn("IsSpeedEligible", self.app.candidate_source.get("1.0", "end"))
        for widget in (self.app.source, self.app.candidate_source):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreater(widget.winfo_height(), 50)
        self.assertLessEqual(self.app.source.winfo_rootx() + self.app.source.winfo_width(),
                             self.app.candidate_source.winfo_rootx())

    def test_candidate_and_history_identify_current_probe_independently_of_original_goal(self):
        self.app.workbench = pedal_workbench()
        self.app.refresh_trace()
        self.assertIn("IsAssistRequested :: pedal", self.app.candidate_context.get())
        key = next(k for k, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        self.assertIn("pedal → pedal", self.app.values.item(key, "values")[2])
        self.app.values.selection_set(key)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="공급자 pedal 조사"):
            self.app.follow(self.app.values)
        current = self.app.workbench.manager.current_step
        self.assertIn("SensorAcquisition_10ms :: pedal", self.app.candidate_context.get())
        self.assertEqual(self.app.history.item(current.id, "values")[4], "pedal")
        self.assertIn("pedal → 60", self.app.goal.get())

    def test_compact_summary_hides_full_paths_and_keeps_details_available(self):
        self.root.deiconify()
        self.root.update()
        self.assertFalse(self.app.settings.winfo_ismapped())
        self.assertNotIn(str(self.app.workbench.project.root), self.app.goal.get())
        self.assertNotIn("경로:", self.app.current_summary.get())
        self.assertIn("경로:", self.app.trace_details.get("1.0", "end"))
        self.app.toggle_settings()
        self.root.update()
        self.assertTrue(self.app.scope_entry.winfo_ismapped())
        self.assertEqual(self.app.inspection_notebook.tab(1, "text"), "근거 상세")

    def test_array_selection_stays_whole_and_disables_unsupported_tracking(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "member.c"
            path.write_text("int F(void) { if (b.a[0] >= 60 && gate) return 1; return 0; }", encoding="utf-8")
            workbench = Workbench()
            workbench.project = analyze_project(directory)
            function = workbench.project.functions[0]
            branch = workbench.project.results[0].branches[0]
            workbench.start(function.id, branch.id, "멤버 구분")
            self.app.workbench = workbench
            self.app.refresh_trace()
            self.assertEqual(self.app.variable_entry["values"], ("b.a[0]", "gate"))
            before = workbench.session
            self.app.variable.set("b.a[0]")
            self.app.choose_branch_input()
            self.assertIn("아직 추적하지", self.app.input_help.get())
            self.assertIn("disabled", self.app.goal_button.state())
            self.assertIn("disabled", self.app.inspect_button.state())
            self.assertEqual(workbench.session, before)
            self.app.variable.set("gate")
            self.app.choose_branch_input()
            self.assertNotIn("disabled", self.app.goal_button.state())

    def test_first_goal_can_start_investigation_after_branch_and_variable_selection(self):
        workbench = self.app.workbench
        function = workbench.session.target_function
        branch = workbench.session.target_branch
        workbench.manager = None
        workbench.dirty = False
        self.app.functions.selection_set(function.id)
        self.app.browse_function()
        self.app.branches.selection_set(branch.id)
        self.app.preview_branch()
        self.app.variable.set("pedal")
        self.app.choose_branch_input()
        self.app.target_value.set("")
        with self.assertRaisesRegex(ValueError, "원하는 값"):
            self.app.set_variable_goal()
        self.assertIsNone(workbench.manager)
        self.app.target_value.set("60")
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value=None):
            self.app.set_variable_goal()
        self.assertIsNone(workbench.manager)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="페달 입력 조사"):
            self.app.set_variable_goal()
        self.assertEqual(workbench.session.variable_goal.variable, "pedal")
        self.assertEqual(workbench.session.variable_goal.target_value, "60")
        data = dict(workbench.project.sources)[branch.location.path]
        goal = workbench.session.variable_goal
        self.assertEqual(data[goal.location.start_byte:goal.location.end_byte], b"pedal")


if __name__ == "__main__":
    unittest.main()
