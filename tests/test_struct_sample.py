"""Fictional multi-function AUTOSAR structure paths, execution, DB and actual Tk."""

from contextlib import closing
from hashlib import sha256
import json
import sqlite3
from pathlib import Path
import tempfile
import gc
import tkinter as tk
import unittest
from unittest.mock import patch

from autosar_trace_navigator.gui import Navigator
from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.workbench import Workbench, analyze_project
from examples.create_struct_demo import SAMPLE, SESSION_IDS, SCOPE, create_struct_database, follow_source, start_struct_investigation
from c_build import run_c99


ROOT = Path(__file__).resolve().parents[1]


class StructSampleTests(unittest.TestCase):
    def test_c_execution_and_analysis_do_not_modify_sample_sources(self):
        def fingerprint():
            return {p: (sha256(p.read_bytes()).digest(), p.stat().st_mtime_ns)
                    for p in SAMPLE.iterdir() if p.suffix in {".c", ".h"}}
        before = fingerprint()
        project = analyze_project(SAMPLE, include_paths=SCOPE)
        self.assertEqual(len(project.sources), 5)
        self.assertEqual(len(project.functions), 14)
        self.assertFalse(any(d.code in {"SYNTAX_ERROR", "MISSING_SYNTAX"} for r in project.results for d in r.diagnostics))
        output = run_c99(sorted(SAMPLE.glob("*.c")), include_dirs=(SAMPLE,))
        self.assertIn("PASS struct paths: 6 scenarios", output)
        self.assertEqual(fingerprint(), before)
        print(output, end="")

    def test_a_through_rte_crosses_six_application_functions_to_controllable_input(self):
        w = start_struct_investigation("Struct_Consume", "a")
        expected = ["b.a", "built.a", "$return.a", "state.a", "out->a", "$return.a", "made.a", "out->a", "Struct_RawInput"]
        kinds = ("assignment", "rte_data", "return_value", "return", "output_parameter", "return_value", "return", "output_parameter", "expression_operand")
        for kind, expression in zip(kinds, expected):
            follow_source(w, kind, expression)
            self.assertEqual(w.manager.current_step.probe.expression, expression)
        self.assertEqual(len({step.function.name for step in w.session.steps}), 6)
        condition, = w.execution_candidates()
        self.assertEqual(condition.probe.expression, "Struct_EnableInput")
        follow_source(w, "ct_global_input")
        self.assertIsNone(w.manager.current_step.probe)
        self.assertEqual(w.session.variable_goal.variable, "a")
        self.assertEqual(w.session.variable_goal.target_value, "60")

    def test_pointer_parameter_and_global_object_keep_distinct_control_meanings(self):
        w = start_struct_investigation("Struct_ConsumePointer", "p->a")
        follow_source(w, "parameter_input", "local.a")
        self.assertEqual(w.manager.current_step.function.name, "Struct_RunPointer")
        self.assertIn("pointer_identity_not_proven", w.manager.current_step.uncertainty)
        global_object = start_struct_investigation("Struct_ConsumeGlobal", "Struct_ExternalState.a")
        self.assertTrue(any(c.probe and c.probe.expression == "built.a" for c in global_object.value_candidates()))
        follow_source(global_object, "object_origin")
        boundary, = (c for c in global_object.value_candidates() if c.value_kind == "ct_global_input")
        self.assertIn("object_origin_not_member_value", boundary.uncertainty)
        self.assertIn("header_visibility_not_verified", boundary.uncertainty)

    def test_generated_db_restores_member_goals_conditions_and_object_alternative(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "struct.sqlite3"
            sessions = create_struct_database(path)
            self.assertEqual([len(s.steps) for s in sessions], [14, 13, 3])
            with TraceStore(path) as store:
                self.assertEqual(store.list_sessions(), SESSION_IDS)
                for session in sessions:
                    self.assertEqual(store.load(session.id).session, session)
                first = store.load(SESSION_IDS[0]).session
                self.assertTrue(any("object_origin_not_member_value" in s.uncertainty for s in first.steps))
                self.assertTrue(any("execution_requirement_true: (Struct_EnableInput == 1u)" in s.uncertainty for s in first.steps))
            with closing(sqlite3.connect(path)) as connection:
                versions = [json.loads(row[0])["format_version"] for row in connection.execute("SELECT payload FROM trace_sessions")]
            self.assertEqual(versions, [3, 3, 3])
            digest = sha256(path.read_bytes()).digest()
            with self.assertRaises(FileExistsError):
                create_struct_database(path)
            self.assertEqual(sha256(path.read_bytes()).digest(), digest)

    def test_bundled_struct_db_is_readable_through_product_storage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "copy.sqlite3"
            path.write_bytes((ROOT / "examples/struct_tutorial.sqlite3").read_bytes())
            with TraceStore(path) as store:
                self.assertEqual(store.list_sessions(), SESSION_IDS)
                self.assertEqual(store.load(SESSION_IDS[1]).session.variable_goal.variable, "p->a")


class StructGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.workbench = start_struct_investigation("Struct_ConsumePointer", "p->a")
        self.workbench.start(self.workbench.session.target_function.id, self.workbench.session.target_branch.id, "포인터 멤버 조사")
        self.app = Navigator(self.root, self.workbench)

    def tearDown(self):
        self.app.workbench.dirty = False
        self.app.close()
        del self.app, self.root
        gc.collect()  # finalize Tk objects on this thread, not in a later worker thread's GC

    def test_member_selector_follow_preview_and_original_goal_are_connected(self):
        self.assertEqual(self.app.variable_entry["values"], ("p->a",))
        self.app.choose_branch_input()
        self.assertNotIn("disabled", self.app.goal_button.state())
        self.app.target_value.set("60")
        self.app.set_variable_goal()
        self.assertEqual(self.app.source.get(*self.app.source.tag_ranges("tracked_value")), "p->a")
        key, = (key for key, candidate in self.app.candidate_map.items() if candidate.value_kind == "parameter_input")
        self.app.values.selection_set(key)
        before = self.workbench.session
        self.app.preview_candidate(self.app.values)
        self.assertIn("p->a → local.a", self.app.preview_label.get())
        self.assertEqual(self.workbench.session, before)
        with patch("autosar_trace_navigator.gui.simpledialog.askstring", return_value="호출 객체 local의 a 조사"):
            self.app.follow(self.app.values)
        self.assertIn("p->a → 60", self.app.goal.get())
        self.assertIn("Struct_RunPointer :: local.a", self.app.candidate_context.get())

    def test_double_click_selects_whole_object_and_parenthesized_pointer_member(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            path = Path(directory) / "member.c"
            source = "typedef struct { int a; } S;\nint F(void) { S b; S *p=&b;\n if (b.a && (*p).a) return 1; return 0; }"
            path.write_text(source, encoding="utf-8")
            w = Workbench()
            w.project = analyze_project(directory)
            fn = w.project.functions[0]
            branch = w.project.results[0].branches[0]
            w.start(fn.id, branch.id, "원본 멤버 선택")
            self.app.workbench = w
            self.app.refresh_trace()
            self.root.deiconify()
            self.root.update()
            before = w.session
            for index, (text, canonical) in enumerate((("b.a", "b.a"), ("(*p).a", "p->a"))):
                displayed = self.app.source.get("3.0", "3.end")
                box = self.app.source.bbox(f"3.{displayed.index(text) + len(text) - 1}")
                self.assertIsNotNone(box)
                time = 1000 + index * 1000
                for event, offset in (("<ButtonPress-1>", 0), ("<ButtonRelease-1>", 1), ("<ButtonPress-1>", 100), ("<ButtonRelease-1>", 101)):
                    self.app.source.event_generate(event, x=box[0]+1, y=box[1]+1, time=time+offset)
                self.root.update()
                self.assertEqual(self.app.variable.get(), canonical)
                self.assertEqual(w.session, before)
                data = dict(w.project.sources)[path]
                self.assertEqual(data[self.app.picked_location.start_byte:self.app.picked_location.end_byte], text.encode())


if __name__ == "__main__":
    unittest.main()
