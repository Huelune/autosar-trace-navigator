"""Verify user decisions and usable compact layout with real Tk widgets."""

import gc
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from test_execution_values import guarded_workbench, follow_kind
from test_value_trace import pedal_workbench


class GuidedUiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Navigator(self.root)

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()
        del self.app, self.root
        gc.collect()  # finalize Tk objects on this thread, not in a later worker thread's GC

    def test_initial_guidance_and_disabled_actions_do_not_open_error_dialogs(self):
        self.assertIn("루트 폴더 선택", self.app.workflow_hint.get())
        buttons = [self.app.toolbar_buttons["세션 저장"], self.app.toolbar_buttons["뒤로"],
                   self.app.toolbar_buttons["선택 범위 분석"], self.app.start_button,
                   self.app.record_button, self.app.history_button, *self.app.follow_buttons.values()]
        with patch("autosar_trace_navigator.gui.messagebox.showerror") as error:
            for button in buttons:
                self.assertIn("disabled", button.state())
                button.invoke()
            error.assert_not_called()
        self.assertIsNone(self.app.workbench.manager)

    def test_enter_prepares_first_goal_instead_of_trying_to_inspect_without_a_trace(self):
        w = pedal_workbench()
        function, branch = w.session.target_function, w.session.target_branch
        w.manager = None
        w.dirty = False
        self.app.workbench = w
        self.app.query.set(function.name)
        self.app.render_project()
        self.app.functions.selection_set(function.id)
        self.app.browse_function()
        self.app.branches.selection_set(branch.id)
        self.app.preview_branch()
        self.app.variable.set("pedal")
        self.app.activate_variable()
        self.assertIsNone(w.manager)
        self.assertEqual(self.app.variable.get(), "pedal")
        self.assertIn("변수 목표 설정", self.app.workflow_hint.get())
        self.assertNotIn("disabled", self.app.start_button.state())

    def test_candidate_preview_enables_only_selected_action_and_follow_clears_selection(self):
        self.app.workbench = pedal_workbench()
        self.app.refresh_trace()
        w = self.app.workbench
        before = w.session
        key = next(k for k, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        self.assertIn("disabled", self.app.follow_buttons[self.app.values].state())
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.assertEqual(w.session, before)
        self.assertNotIn("disabled", self.app.follow_buttons[self.app.values].state())
        self.assertIn("disabled", self.app.follow_buttons[self.app.calls].state())
        self.assertIn("연결 미확정", self.app.preview_summary.get())
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="공급자 코드 조사"):
            self.app.follow_buttons[self.app.values].invoke()
        self.assertNotEqual(w.session.current_step_id, before.current_step_id)
        self.assertIn("disabled", self.app.follow_buttons[self.app.values].state())
        self.assertNotIn("disabled", self.app.toolbar_buttons["뒤로"].state())
        self.assertIn("pedal → 60", self.app.goal.get())

    def test_inline_conditions_counts_and_ct_guidance_are_conservative(self):
        w = guarded_workbench()
        follow_kind(w, "rte_data")
        self.app.workbench = w
        self.app.refresh_trace()
        key = next(k for k, c in self.app.candidate_map.items()
                   if c.value_kind == "expression_operand" and c.probe.expression == "ValuePath_RawInput")
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.assertIn("조건", self.app.preview_summary.get())
        self.assertIn("조건 3개 (참 2 · 거짓 1)", self.app.preview_summary.get())
        self.assertIn("도달 미증명", self.app.detail.get("1.0", "end"))
        for index, table in enumerate(self.app.candidate_tables):
            self.assertIn(f"({len(table.get_children())})", self.app.candidates_notebook.tab(index, "text"))
        follow_kind(w, "expression_operand", "ValuePath_RawInput")
        follow_kind(w, "ct_global_input")
        self.app.refresh_trace()
        self.assertIn("CT 접근성과 설정값", self.app.workflow_hint.get())
        self.assertNotIn("충족 완료", self.app.workflow_hint.get())

    def test_compact_workspace_keeps_code_and_action_visible_and_respects_manual_sashes(self):
        self.app.workbench = pedal_workbench()
        self.app.refresh_trace()
        self.app.toggle_settings()  # Normal investigation workspace after analysis hides settings.
        self.root.geometry("1100x760")
        self.root.deiconify()
        self.root.update()
        key = next(k for k, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.root.update()
        for widget in (self.app.source, self.app.candidate_source):
            self.assertGreater(widget.winfo_height(), 50,
                               (str(widget), self.app.comparison_pane.winfo_height(),
                                self.app.comparison_pane.sashpos(0), self.app.comparison_pane.sashpos(1),
                                self.app.preview_summary_label.winfo_height()))
            self.assertGreater(widget.winfo_width(), 250)
        for widget in (self.app.follow_buttons[self.app.values], self.app.history_button):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreater(widget.winfo_height(), 20)
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
        self.app.comparison_pane.sashpos(0, 175)
        self.root.update()
        position = self.app.comparison_pane.sashpos(0)
        self.app.refresh_trace()
        self.root.update()
        self.assertEqual(self.app.comparison_pane.sashpos(0), position)


if __name__ == "__main__":
    unittest.main()
