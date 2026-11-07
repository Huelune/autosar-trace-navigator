"""Reference code stays fixed while candidate/current/history functions change."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.workbench import Workbench, analyze_project
from test_value_trace import pedal_workbench


ROOT = Path(__file__).resolve().parents[1]


class StageCodeTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Navigator(self.root, pedal_workbench())
        self.root.deiconify()
        self.root.update()

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()

    def reference(self):
        return (self.app.source.get("1.0", "end"), self.app.source.yview(),
                self.app.source.xview(), self.app.source_label.get(),
                tuple(map(str, self.app.source.tag_ranges("location"))),
                tuple(map(str, self.app.source.tag_ranges("tracked_value"))))

    def advance(self, kind):
        key = next(k for k, c in self.app.candidate_map.items() if c.value_kind == kind)
        self.app.values.selection_set(key)
        self.app.preview_candidate(self.app.values)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="다음 공급 함수 조사"):
            self.app.follow(self.app.values)
        self.root.update()

    def test_multifile_follow_keeps_reference_and_shows_each_current_function_without_blank_reset(self):
        reference = self.reference()
        goal = self.app.workbench.session.variable_goal
        for kind in ("rte_data", "return_value", "return", "global_write"):
            self.advance(kind)
            step = self.app.workbench.manager.current_step
            self.assertEqual(self.reference(), reference)
            self.assertIn("현재 조사 단계", self.app.preview_label.get())
            self.assertIn(step.function.name, self.app.preview_label.get())
            self.assertIn(step.function.name, self.app.candidate_source.get("1.0", "end"))
            self.assertEqual(self.app.preview_location, step.selected_location)
            self.assertEqual(self.app.workbench.session.variable_goal, goal)
        self.assertNotEqual(self.app.preview_location.path, self.app.source_location.path)

    def test_history_preview_explicit_move_and_back_change_only_stage_code(self):
        reference = self.reference()
        root_step = self.app.workbench.manager.current_step
        self.advance("rte_data")
        previous = self.app.workbench.manager.current_step
        self.advance("return_value")
        before = self.app.workbench.session
        self.app.history.selection_set(previous.id)
        self.app.preview_history()
        self.root.update()
        self.assertEqual(self.app.workbench.session, before)
        self.assertIn(previous.function.name, self.app.preview_label.get())
        self.assertIn("이력 코드", self.app.preview_label.get())
        self.assertEqual(self.reference(), reference)
        self.app.select_history()
        self.root.update()
        self.assertEqual(self.app.workbench.manager.current_step.id, previous.id)
        self.assertIn("현재 조사 단계", self.app.preview_label.get())
        self.app.back()
        self.root.update()
        self.assertEqual(self.app.workbench.manager.current_step.id, root_step.id)
        self.assertIn(root_step.function.name, self.app.preview_label.get())
        self.assertEqual(self.reference(), reference)

    def test_stage_double_click_maps_unicode_and_function_offset_to_its_own_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            root_path, next_path = Path(directory) / "root.c", Path(directory) / "next.c"
            root_path.write_text("int Next(int);\nint Root(void) { int a=Next(60); if(a>0) return 1; return 0; }", encoding="utf-8")
            next_path.write_bytes(("\n" * 8 + "int Next(int input) {\n /*한글*/ return input;\n}\n").encode())
            w = Workbench()
            w.project = analyze_project(directory)
            fn = w.project.functions_by_name["Root"][0]
            branch = next(b for r in w.project.results for b in r.branches if b.function_id == fn.id)
            w.start(fn.id, branch.id, "고정 소스와 별도 함수 조사")
            w.set_variable_goal("a", "60", branch.location)
            self.app.workbench = w
            self.app.render_project()
            self.app.refresh_trace()
            self.root.update()
            reference = self.reference()
            self.advance("return_value")
            self.assertGreater(self.app.preview_first_line, 1)
            row = 10 - self.app.preview_first_line + 1
            widget = self.app.candidate_source
            line = widget.get(f"{row}.0", f"{row}.end")
            box = widget.bbox(f"{row}.{line.index('input') + 1}")
            self.assertIsNotNone(box)
            before = w.session
            for event, time in (("<ButtonPress-1>", 1000), ("<ButtonRelease-1>", 1001),
                                ("<ButtonPress-1>", 1100), ("<ButtonRelease-1>", 1101)):
                widget.event_generate(event, x=box[0]+1, y=box[1]+1, time=time)
            self.root.update()
            site = self.app.picked_location
            self.assertEqual(site.path, next_path)
            self.assertEqual(site.start_line, 10)
            self.assertEqual(next_path.read_bytes()[site.start_byte:site.end_byte], b"input")
            self.assertEqual(w.session, before)
            self.assertEqual(self.reference(), reference)
            self.assertNotIn("disabled", self.app.inspect_button.state())
            self.app.inspect_variable()
            self.assertEqual(w.manager.current_step.probe.expression, "input")
            self.app.pick_source_position("2.40")
            self.assertIn("disabled", self.app.record_button.state())
            self.assertIn("disabled", self.app.inspect_button.state())
            with self.assertRaises(ValueError):
                self.app.record_location()

    def test_restore_without_sources_clears_stage_and_reanalysis_reconnects_both_views(self):
        self.advance("rte_data")
        w = self.app.workbench
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "stage.sqlite3"
            w.save(path)
            restored = Workbench()
            restored.restore(path, w.session.id)
            self.app.workbench = restored
            self.app.refresh_trace()
            self.root.update()
            self.assertIn("소스가 없습니다", self.app.candidate_source.get("1.0", "end"))
            self.assertIsNone(self.app.preview_location)
            self.assertFalse(self.app.pick_source_position("1.10", preview=True))
            restored.project = w.project
            self.app.render_project()
            self.app.refresh_trace()
            self.root.update()
            self.assertIn("IsAssistRequested", self.app.source.get("1.0", "end"))
            self.assertIn("SensorAcquisition_10ms", self.app.candidate_source.get("1.0", "end"))
            self.assertEqual(restored.session, w.session)
            self.assertFalse(restored.dirty)

    def test_explicit_function_browse_changes_reference_but_follow_does_not(self):
        w = self.app.workbench
        before = w.session
        self.app.query.set("IoHwAb_ReadPedalPercent")
        self.app.search_functions()
        fn = w.project.functions_by_name["IoHwAb_ReadPedalPercent"][0]
        self.app.functions.selection_set(fn.id)
        self.app.browse_function()
        self.root.update()
        self.assertEqual(w.session, before)
        reference = self.reference()
        self.advance("rte_data")
        self.assertEqual(self.reference(), reference)
        w.start(before.target_function.id, before.target_branch.id, "새 조사")
        self.app.refresh_trace()
        self.root.update()
        self.assertEqual(self.app.source_location.path, before.target_branch.location.path)
        self.assertIn(before.target_function.name, self.app.source.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
