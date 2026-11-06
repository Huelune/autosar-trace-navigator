"""Real Tk widget tests; no screenshots or mocked widget implementation."""

from concurrent.futures import Future
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.workbench import analyze_project
from test_workbench import sample_workbench


ROOT = Path(__file__).resolve().parents[1]


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Navigator(self.root, sample_workbench())
        self.app.scopes.set(".")
        self.root.update_idletasks()

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()

    def test_goal_reason_source_readonly_and_distinct_candidate_tables(self):
        self.assertIn("mode == BRAKE_ASSIST", self.app.goal.get())
        self.assertIn("ASSIST 조건 조사", self.app.context.get())
        self.assertEqual(self.app.source.cget("state"), "disabled")
        self.assertEqual(self.app.diagnostics.cget("state"), "disabled")
        self.assertIn("void BrakeControl_10ms", self.app.source.get("1.0", "end"))
        self.assertTrue(self.app.calls.get_children())
        self.assertFalse(self.app.rte.get_children())

    def test_function_list_is_search_driven_and_keeps_current_function(self):
        current = self.app.workbench.manager.current_step.function
        self.assertEqual(self.app.functions.get_children(), (current.id,))
        self.app.query.set("SpeedSignal.c")
        self.app.search_functions()
        self.assertEqual(len(self.app.functions.get_children()), 4)  # Three matches and current.
        self.assertTrue(self.app.functions.exists(current.id))
        self.app.query.set("no_matching_function")
        self.app.search_functions()
        self.assertEqual(self.app.functions.get_children(), (current.id,))
        self.assertIn("0개 일치", self.app.search_summary.get())
        self.assertEqual(self.app.workbench.session.target_branch.location.start_line, 10)

    def test_large_function_search_renders_only_page_and_current_pin(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = Path(directory) / "large.c"
            path.write_text("\n".join(f"int Fn{i:03}(void) {{ if (1) return 1; else return 0; }}"
                                      for i in range(550)), encoding="utf-8")
            project = analyze_project(directory, include_paths=("large.c",))
            self.app.workbench.project = project
            self.app.workbench.start(project.functions[0].id, project.results[0].branches[0].id, "범위 테스트")
            self.app.render_project()
            self.app.refresh_trace()
            self.assertEqual(len(self.app.functions.get_children()), 1)
            self.app.query.set("fn")
            self.app.search_functions()
            self.assertEqual(len(self.app.functions.get_children()), 100)
            self.app.change_page(100)
            self.assertEqual(len(self.app.functions.get_children()), 101)
            self.assertTrue(self.app.functions.exists(project.functions[0].id))
            self.app.query.set("fn549")
            self.app.change_page(100)  # Changed query restarts pagination.
            self.assertEqual(self.app.page_offset, 0)
            self.assertEqual(len(self.app.functions.get_children()), 2)
            self.assertEqual(self.app.workbench.session.target_function.name, "Fn000")

    def test_root_selection_does_not_analyze_and_blank_scope_is_rejected(self):
        before = self.app.workbench.project
        with patch("autosar_trace_navigator.gui.filedialog.askdirectory", return_value=str(ROOT)), \
                patch.object(self.app.executor, "submit") as submit:
            self.app.choose_project()
            submit.assert_not_called()
            self.app.scopes.set("")
            with self.assertRaises(ValueError):
                self.app.begin_analysis(ROOT)
            submit.assert_not_called()
        self.assertFalse(self.app.busy)
        self.assertIs(self.app.workbench.project, before)

    def test_compact_layout_keeps_scope_search_and_start_accessible(self):
        self.root.geometry("1100x760")
        self.root.deiconify()
        self.root.update()
        for widget in (self.app.scope_entry, self.app.exclude_entry,
                       *(b for b in self.app.buttons if b.cget("text") in
                         {"검색", "이전", "다음", "선택 분기로 새 조사 시작"})):
            with self.subTest(widget=widget):
                self.assertTrue(widget.winfo_ismapped())
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height())

    def test_follow_button_preserves_target_and_back_keeps_history(self):
        goal = self.app.goal.get()
        key = next(key for key, candidate in self.app.candidate_map.items()
                   if candidate.function and candidate.function.name == "EvaluateBrakeMode")
        self.app.calls.selection_set(key)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="mode 계산 이유"):
            self.app.follow(self.app.calls)
        self.assertEqual(self.app.goal.get(), goal)
        self.assertIn("mode 계산 이유", self.app.context.get())
        self.app.back()
        self.assertEqual(len(self.app.history.get_children()), 2)
        self.assertEqual(self.app.goal.get(), goal)

    def test_analysis_success_and_error_preserve_active_session(self):
        before = self.app.workbench.session
        project = self.app.workbench.project
        for success in (True, False):
            future = Future()
            if success:
                future.set_result(project)
            else:
                future.set_exception(OSError("simulated read error"))
            with patch.object(self.app.executor, "submit", return_value=future), \
                    patch("autosar_trace_navigator.gui.messagebox.showerror") as error:
                self.app.begin_analysis(project.root)
                self.assertTrue(self.app.busy)
                self.assertIn("disabled", self.app.buttons[0].state())
                self.root.after_cancel(self.app.poll_id)
                self.app.poll_analysis()
                self.assertFalse(self.app.busy)
                self.assertNotIn("disabled", self.app.buttons[0].state())
                self.assertEqual(self.app.workbench.session, before)
                self.assertEqual(error.call_count, 0 if success else 1)

    def test_actual_background_analysis_completes_on_tk_thread(self):
        self.app.exclusions.set("parser_cases")
        self.app.scopes.set("include;src;support")
        self.app.begin_analysis(ROOT / "test")
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)
        self.assertIn("분석 완료", self.app.status.get())
        self.assertIn("파일 11개", self.app.status.get())
        self.assertIn("소스 변경 여부 미검증", self.app.context.get())

    def test_import_does_not_create_a_window(self):
        result = subprocess.run([sys.executable, "-c",
            "import autosar_trace_navigator.gui; import tkinter; assert tkinter._default_root is None"],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_new_target_requires_reason_and_can_be_cancelled(self):
        before = self.app.workbench.session
        self.app.branches.selection_set(before.target_branch.id)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value=None):
            self.app.start()
        self.assertEqual(self.app.workbench.session, before)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="새 목표"), \
                patch("autosar_trace_navigator.gui.messagebox.askyesno", return_value=False):
            self.app.start()
        self.assertEqual(self.app.workbench.session, before)

    def test_save_and_restored_warning_rendered(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            database = Path(directory) / "widgets.sqlite3"
            with patch("autosar_trace_navigator.gui.filedialog.asksaveasfilename", return_value=str(database)):
                self.app.save()
            self.assertFalse(self.app.workbench.dirty)
            self.assertIn("저장 완료", self.app.status.get())
            self.app.workbench.restore(database, self.app.workbench.session.id)
            self.app.refresh_trace()
            self.assertIn("소스 변경 여부 미검증", self.app.context.get())

    def test_restore_picker_is_centered_and_click_callback_loads_selected_session(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            database = Path(directory) / "picker.sqlite3"
            self.app.workbench.save(database)
            self.root.deiconify()
            self.root.update_idletasks()
            with patch("autosar_trace_navigator.gui.filedialog.askopenfilename", return_value=str(database)):
                self.app.restore()
            self.root.update_idletasks()
            dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
            self.assertGreaterEqual(dialog.winfo_rootx(), self.root.winfo_rootx())
            self.assertGreaterEqual(dialog.winfo_rooty(), self.root.winfo_rooty())
            self.assertLessEqual(dialog.winfo_rootx() + dialog.winfo_width(),
                                 self.root.winfo_rootx() + self.root.winfo_width() + 4)
            table_frame = next(w for w in dialog.winfo_children() if isinstance(w, tk.ttk.Frame))
            table = next(w for w in table_frame.winfo_children() if isinstance(w, tk.ttk.Treeview))
            table.selection_set(self.app.workbench.session.id)
            button = next(w for w in dialog.winfo_children() if isinstance(w, tk.ttk.Button))
            button.invoke()
            self.assertTrue(self.app.workbench.restored)
            self.assertIn("세션 복원 완료", self.app.status.get())

    def test_errors_visible_and_unsaved_close_can_be_cancelled(self):
        with patch("autosar_trace_navigator.gui.messagebox.showerror") as dialog:
            self.app.run_action(lambda: self.app.workbench.start("missing", "missing", "이유"))
            dialog.assert_called_once()
        with patch("autosar_trace_navigator.gui.messagebox.askyesno", return_value=False):
            self.app.close()
        self.assertFalse(self.app.closed)
        self.assertTrue(self.root.winfo_exists())


if __name__ == "__main__":
    unittest.main()
