"""Verify the shipped walkthrough, source preservation and actual Tk restoration."""

from hashlib import sha256
from pathlib import Path
import tempfile
import gc
import tkinter as tk
import unittest

from examples.create_demo import SAMPLE, SESSION_IDS, create_demo_database
from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.workbench import Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]


class TutorialTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)

    def test_creation_preserves_sources_and_records_both_input_plans(self):
        def fingerprint():
            return {p: (sha256(p.read_bytes()).digest(), p.stat().st_mtime_ns)
                    for p in SAMPLE.iterdir() if p.suffix in {".c", ".h"}}
        before = fingerprint()
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "tutorial.sqlite3"
            sessions = create_demo_database(database)
            with TraceStore(database) as store:
                self.assertEqual(store.list_sessions(), SESSION_IDS)
                for session, count in zip(sessions, (4, 10)):
                    self.assertEqual(store.load(session.id).session, session)
                    self.assertEqual(len(session.steps), count)
                    self.assertEqual(session.variable_goal.variable, "pedal")
                    self.assertEqual(session.variable_goal.target_value, "60")
                    self.assertEqual(session.target_branch.location.start_line, 52)
                nested = sessions[1]
                calculation = nested.steps[2]
                self.assertEqual(nested.current_step_id, calculation.id)
                self.assertEqual(calculation.selected_location.start_line, 40)
                self.assertEqual(sum(s.parent_id == calculation.id for s in nested.steps), 3)
                enable = nested.steps[7]
                self.assertIsNone(enable.probe)
                self.assertIn("ct_accessibility_not_verified", enable.uncertainty)
                self.assertIn("execution_requirement_true: (ValuePath_EnableInput == 1u)", enable.uncertainty)
                self.assertIn("execution_requirement_true: (value_path_permit != 0u)", enable.uncertainty)
                self.assertIn("ValuePath_EnableInput=1", enable.reason)
                self.assertIn("ValuePath_ModeInput=2", nested.steps[9].reason)
        self.assertEqual(fingerprint(), before)

    def test_existing_file_and_invalid_output_are_not_modified(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "existing.sqlite3"
            database.write_bytes(b"existing user file")
            with self.assertRaises(FileExistsError):
                create_demo_database(database)
            self.assertEqual(database.read_bytes(), b"existing user file")
            invalid = Path(directory) / "source.c"
            with self.assertRaises(ValueError):
                create_demo_database(invalid)
            self.assertFalse(invalid.exists())

    def test_bundled_database_contains_explained_history(self):
        # TraceStore opens SQLite for writing, so inspect a temporary copy of the artifact.
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "copy.sqlite3"
            database.write_bytes((ROOT / "examples/tutorial.sqlite3").read_bytes())
            with TraceStore(database) as store:
                self.assertEqual(store.list_sessions(), SESSION_IDS)
                for session_id, count in zip(SESSION_IDS, (4, 10)):
                    session = store.load(session_id).session
                    self.assertEqual(len(session.steps), count)
                    self.assertEqual(session.variable_goal.target_value, "60")
                    self.assertTrue(all(s.selected_location is not None and s.reason for s in session.steps))
                    self.assertTrue(all(s.function.location.path.name == "value_paths.c" for s in session.steps))

    def test_generated_sessions_restore_in_gui_and_reconnect_to_source_preview(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            database = Path(directory) / "tutorial.sqlite3"
            create_demo_database(database)
            root = tk.Tk()
            root.withdraw()
            app = Navigator(root)
            try:
                for session_id in SESSION_IDS:
                    workbench = Workbench()
                    workbench.restore(database, session_id)
                    app.workbench = workbench
                    app.refresh_trace()
                    root.update_idletasks()
                    self.assertIn("pedal → 60", app.goal.get())
                    self.assertEqual(len(app.history.get_children()), len(workbench.session.steps))
                    self.assertFalse(workbench.dirty)
                    workbench.project = analyze_project(SAMPLE, include_paths=("value_paths.c", "value_paths.h"))
                    app.render_project()
                    app.refresh_trace()
                    root.update_idletasks()
                    self.assertIn("ValuePath_RawInput * 2u + 10u", app.source.get("1.0", "end"))
                    if session_id == SESSION_IDS[0]:
                        self.assertIn("CT 전역 후보에서 값 추적 중지", app.context.get())
                        self.assertFalse(app.values.get_children())
                    else:
                        self.assertTrue(app.requirements.get_children())
                        before = workbench.session
                        app.history.selection_set(workbench.session.steps[7].id)
                        app.preview_history()
                        self.assertIn("value_path_permit = 1u", app.candidate_source.get("1.0", "end"))
                        self.assertIn("ValuePath_EnableInput=1", app.detail.get("1.0", "end"))
                        self.assertEqual(workbench.session, before)
                        self.assertFalse(workbench.dirty)
            finally:
                app.workbench.dirty = False
                app.close()
                del app, root
                gc.collect()  # finalize Tk objects on this thread, not in a later worker thread's GC


if __name__ == "__main__":
    unittest.main()
