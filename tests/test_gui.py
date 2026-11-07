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
from test_value_trace import pedal_workbench


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
        self.app.toggle_settings()
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

    def use_pedal_goal(self):
        self.app.workbench = pedal_workbench()
        self.app.render_project()
        self.app.refresh_trace()

    def test_candidate_code_preview_does_not_change_cursor_dirty_or_source_selection(self):
        self.app.workbench.dirty = False
        before = self.app.workbench.session
        location = self.app.picked_location
        key = next(key for key, c in self.app.candidate_map.items()
                   if c.function and c.function.name == "EvaluateBrakeMode")
        self.app.calls.selection_set(key)
        self.app.preview_candidate(self.app.calls)
        self.assertIn("EvaluateBrakeMode", self.app.candidate_source.get("1.0", "end"))
        self.assertEqual(self.app.candidate_source.cget("state"), "disabled")
        self.assertNotIn(str(self.app.preview_tab), self.app.source_notebook.tabs())
        self.assertEqual(self.app.source_notebook.select(), self.app.source_notebook.tabs()[0])
        self.assertEqual(self.app.workbench.session, before)
        self.assertFalse(self.app.workbench.dirty)
        self.assertEqual(self.app.picked_location, location)

    def test_unresolved_candidate_preview_replaces_previous_code(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = Path(directory) / "preview.c"
            path.write_text("int Known(void) { return 1; }\n"
                            "int F(void) { if (1) Known(); Missing(); return 0; }", encoding="utf-8")
            project = analyze_project(directory)
            self.app.workbench.project = project
            function = project.functions_by_name["F"][0]
            self.app.workbench.start(function.id, project.results[0].branches[0].id, "미확인 후보 확인")
            self.app.refresh_trace()
            for name in ("Known", "Missing"):
                key = next(key for key, c in self.app.candidate_map.items() if c.label == name)
                self.app.calls.selection_set(key)
                self.app.preview_candidate(self.app.calls)
            text = self.app.candidate_source.get("1.0", "end")
            self.assertIn("대상 함수 미확인", text)
            self.assertIn("Missing()", text)
            self.assertNotIn("int Known", text)
            self.assertEqual(len(self.app.workbench.session.steps), 1)

    def test_value_sources_follow_updates_probe_but_preserves_goal_and_records_destination_line(self):
        self.use_pedal_goal()
        goal = self.app.workbench.session.variable_goal
        self.assertIn("pedal → 60", self.app.goal.get())
        key = next(key for key, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        candidate = self.app.candidate_map[key]
        self.assertIn(key, self.app.values.get_children())
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.assertIn("Rte_Write_Pedal_Percent", self.app.candidate_source.get("1.0", "end"))
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="pedal 공급 입력 조사"):
            self.app.follow(self.app.values)
        step = self.app.workbench.manager.current_step
        self.assertEqual(step.function.name, "SensorAcquisition_10ms")
        self.assertEqual(step.selected_location, candidate.selected_location)
        self.assertEqual(self.app.workbench.session.variable_goal, goal)
        self.assertIn("현재 값 조사: pedal", self.app.context.get())
        self.assertTrue(self.app.history.item(step.id, "values")[2].startswith(
            f"{candidate.selected_location.start_line}행"))

    def test_selected_line_and_history_preview_are_explicit_and_return_to_recorded_line(self):
        self.use_pedal_goal()
        before = self.app.workbench.session
        self.app.pick_source_position("16.23")
        self.assertEqual(self.app.workbench.session, before)  # Merely clicking is read-only.
        selected = self.app.picked_location
        self.app.record_location()
        root_step = self.app.workbench.manager.current_step
        key = next(key for key, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        self.app.values.selection_set(key)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="입력 공급자"):
            self.app.follow(self.app.values)
        before = self.app.workbench.session
        self.app.history.selection_set(root_step.id)
        self.app.preview_history()
        self.assertEqual(self.app.workbench.session, before)
        self.assertIn("선택 위치:", self.app.detail.get("1.0", "end"))
        self.app.select_history()
        self.assertEqual(self.app.picked_location, selected)
        self.assertEqual(self.app.workbench.manager.current_step.selected_location, selected)
        self.assertIn("16.0", tuple(str(index) for index in self.app.source.tag_ranges("location")))

    def test_goal_controls_and_current_variable_change_survive_save_restore(self):
        self.use_pedal_goal()
        self.app.workbench.start(self.app.workbench.session.target_function.id,
                                 self.app.workbench.session.target_branch.id, "새 변수 목표")
        self.app.refresh_trace()
        self.app.variable.set("pedal")
        self.app.target_value.set("60")
        self.app.set_variable_goal()
        goal = self.app.workbench.session.variable_goal
        self.app.variable.set("eligible")
        self.app.inspect_variable()
        self.assertEqual(self.app.workbench.session.variable_goal, goal)
        self.assertIn("현재 값 조사: eligible", self.app.context.get())
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "goal.sqlite3"
            self.app.workbench.save(database)
            self.app.workbench.restore(database, self.app.workbench.session.id)
            self.app.refresh_trace()
            self.assertIn("pedal → 60", self.app.goal.get())
            self.assertEqual(self.app.picked_location, goal.location)
            self.assertTrue(self.app.values.get_children())

    def test_source_position_uses_byte_columns_after_unicode_comment_and_rejects_other_function(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "unicode.c"
            source = "int F(void) {\n int value=0;\n /*한글*/ if (value>=60) return 1;\n return 0;\n}\nint Other(void) { return 0; }"
            path.write_text(source, encoding="utf-8")
            project = analyze_project(directory)
            self.app.workbench.project = project
            function = project.functions_by_name["F"][0]
            self.app.workbench.start(function.id, project.results[0].branches[0].id, "한글 위치")
            self.app.refresh_trace()
            line = source.splitlines()[2]
            self.app.pick_source_position(f"3.{7 + line.index('value')}")
            location = self.app.picked_location
            self.assertEqual(location.start_byte, dict(project.sources)[path].index(b"value>=60"))
            self.assertEqual(location.start_column, len(line[:line.index('value')].encode()) + 1)
            self.app.record_location()
            before = self.app.workbench.session
            self.app.show_source(project.functions_by_name["Other"][0].location)
            with self.assertRaises(ValueError):
                self.app.record_location()
            self.assertEqual(self.app.workbench.session, before)

    def test_compact_layout_with_variable_goal_keeps_new_controls_and_history_button_accessible(self):
        self.use_pedal_goal()
        self.root.geometry("1100x760")
        self.root.deiconify()
        self.root.update()
        self.assertFalse(self.app.goal_controls.winfo_ismapped())  # Original goal is already fixed.
        for widget in (self.app.variable_entry,
                       *(b for b in self.app.buttons if b.cget("text") in
                         {"선택 라인 기록", "현재 변수 조사", "선택한 이력 단계로 이동",
                          "선택 분기로 새 조사 시작"})):
            with self.subTest(widget=widget):
                self.assertTrue(widget.winfo_ismapped())
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height())

    def test_source_mouse_release_records_line_only_after_explicit_button(self):
        self.use_pedal_goal()
        self.root.deiconify()
        self.root.update()
        self.app.source.see("16.23")
        self.root.update_idletasks()
        box = self.app.source.bbox("16.23")
        self.assertIsNotNone(box)
        before = self.app.workbench.session
        self.app.source.event_generate("<ButtonRelease-1>", x=box[0] + 1, y=box[1] + 1)
        self.root.update()
        self.assertEqual(self.app.picked_location.start_line, 16)
        self.assertEqual(self.app.workbench.session, before)
        button = next(b for b in self.app.buttons if b.cget("text") == "선택 라인 기록")
        button.invoke()
        self.assertEqual(self.app.workbench.manager.current_step.selected_location, self.app.picked_location)

    def test_history_preview_declines_mismatched_function_snapshot(self):
        self.app.workbench.project = analyze_project(ROOT / "test" / "large_autosar",
                                                     include_paths=("swc/Brake_000", "shared"))
        before = self.app.workbench.session
        self.app.history.selection_set(before.current_step_id)
        self.app.preview_history()
        self.assertIn("일치하지 않아", self.app.candidate_source.get("1.0", "end"))
        self.assertEqual(self.app.workbench.session, before)

    def test_location_labels_show_actual_line_before_long_function_or_path(self):
        self.use_pedal_goal()
        step = self.app.workbench.manager.current_step
        self.assertTrue(self.app.history.item(step.id, "values")[2].startswith("16행"))
        key = next(key for key, c in self.app.candidate_map.items() if c.value_kind == "rte_data")
        candidate = self.app.candidate_map[key]
        self.assertNotEqual(candidate.selected_location.start_line, candidate.function.location.start_line)
        self.assertTrue(self.app.values.item(key, "values")[1].startswith(
            f"{candidate.selected_location.start_line}행"))
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        self.assertIn(candidate.function.name, self.app.preview_label.get())

    def test_double_click_variable_populates_input_without_mutating_session(self):
        self.use_pedal_goal()
        self.root.deiconify()
        self.root.update()
        self.app.variable.set("")
        text = self.app.source.get("16.0", "16.end")
        column = text.index("pedal") + 1
        box = self.app.source.bbox(f"16.{column}")
        self.assertIsNotNone(box)
        before = self.app.workbench.session
        for event, timestamp in (("<ButtonPress-1>", 1000), ("<ButtonRelease-1>", 1001),
                                 ("<ButtonPress-1>", 1100), ("<ButtonRelease-1>", 1101)):
            self.app.source.event_generate(event, x=box[0] + 1, y=box[1] + 1, time=timestamp)
        self.root.update()
        self.assertEqual(self.app.variable.get(), "pedal")
        self.assertEqual(self.app.workbench.session, before)

    def test_terminal_line_stays_visible_after_preview_and_follow_layout_change(self):
        self.use_pedal_goal()
        self.root.deiconify()
        self.root.update()
        for kind in ("rte_data", "return_value", "return", "global_write", "constant"):
            key = next(key for key, c in self.app.candidate_map.items()
                       if c.value_kind == kind and (kind != "constant" or c.label.endswith("60u")))
            self.app.values.selection_set(key)
            self.app.preview_candidate(self.app.values)
            self.root.update()
            with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="입력 출처"):
                self.app.follow(self.app.values)
            self.root.update()
        location = self.app.workbench.manager.current_step.selected_location
        box = self.app.source.bbox(f"{location.start_line}.0")
        self.assertIsNotNone(box)
        self.assertLessEqual(box[1] + box[3], self.app.source.winfo_height())
        # A newer user click must win over a still-pending viewport callback.
        self.app.show_source(location)
        self.app.pick_source_position("34.12")
        self.root.update()
        self.assertEqual(self.app.picked_location.start_line, 34)


if __name__ == "__main__":
    unittest.main()
