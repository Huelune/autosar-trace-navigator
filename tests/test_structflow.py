"""Object identity, aggregate projection and explicit pointer/RTE candidates."""

from pathlib import Path
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest

from autosar_trace_navigator.access import parse_access_path
from autosar_trace_navigator.models import SourceRange, ValueProbe
from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.workbench import Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]
TYPE = "typedef struct { unsigned a; unsigned other; } State;\n"


class StructflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)

    def project(self, source):
        (self.folder / "sample.c").write_text(TYPE + source, encoding="utf-8")
        return analyze_project(self.folder)

    def probe(self, project, function, expression, marker=None):
        fn = project.functions_by_name[function][0]
        data = dict(project.sources)[fn.location.path]
        offset = data.index((marker or expression).encode(), fn.location.start_byte)
        prefix = data[:offset]
        line, column = prefix.count(b"\n") + 1, len(prefix.rsplit(b"\n", 1)[-1]) + 1
        location = SourceRange(fn.location.path, line, column, line, column + len(expression), offset, offset + len(expression))
        return ValueProbe(fn.id, expression, location)

    def test_access_paths_keep_object_member_and_indirection_distinct(self):
        path = parse_access_path(" b . inner -> a ")
        self.assertEqual(path.root, "b")
        self.assertEqual(path.expression, "b.inner->a")
        self.assertTrue(path.indirect)
        self.assertEqual(parse_access_path("*out").expression, "*out")
        for invalid in ("a b", "b..a", "b[a]", "a()", "*b.a", "b+a"):
            self.assertIsNone(parse_access_path(invalid), invalid)

    def test_direct_member_writes_do_not_merge_other_objects_or_bare_names(self):
        project = self.project("int F(void) { State b; State c; unsigned a=999; b.a=60; c.a=90; "
                               "if (b.a>=60) return 1; b.a=100; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=60"))
        writes = [r for r in rows if r.kind == "constant"]
        self.assertEqual([r.expression for r in writes], ["60"])
        self.assertEqual(next(r for r in rows if r.kind == "object_origin").next_probe.expression, "b")

    def test_whole_object_copy_and_designated_initialization_preserve_member(self):
        project = self.project("int F(void) { State other={.a=25,.other=99}; State b; b=other; "
                               "if (b.a>=25) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=25"))
        copied = next(r for r in rows if r.kind == "member_write")
        self.assertEqual(copied.next_probe.expression, "other.a")
        sources = project.value_resolver.sources(copied.next_probe)
        self.assertEqual([r.expression for r in sources if r.kind == "constant"], ["25"])
        self.assertNotIn("99", [r.expression for r in sources])

    def test_nested_designators_and_unmapped_positional_initializers_are_distinct(self):
        project = self.project("int F(void) { struct { State inner; } b={.inner={.a=17}}; "
                               "if (b.inner.a>=17) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.inner.a", "b.inner.a>=17"))
        self.assertIn("17", [r.expression for r in rows if r.kind == "constant"])
        project = self.project("int F(void) { State b={17,99}; if (b.a) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a)"))
        boundary = next(r for r in rows if r.kind == "member_boundary")
        self.assertIn("aggregate_source_shape_not_resolved", boundary.uncertainty)

    def test_explicit_pointer_initialization_and_alias_write_reach_object(self):
        project = self.project("int F(void) { State b={.a=1}; State *p=&b; State *q=p; q->a=60; "
                               "if (b.a>=60) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=60"))
        write = next(r for r in rows if r.expression == "60")
        self.assertIn("alias_candidates_not_reaching_definitions", write.uncertainty)
        project = self.project("int F(void) { State b={.a=4}; State *p=&b; if (p->a>=4) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "p->a", "p->a>=4"))
        bound = next(r for r in rows if r.kind == "member_initializer")
        self.assertEqual(bound.next_probe.expression, "b.a")
        self.assertIn("pointer_identity_not_proven", bound.uncertainty)

    def test_ambiguous_pointer_assignments_remain_candidates(self):
        project = self.project("int F(int gate) { State b,c; State *p=&b; if(gate) p=&c; p->a=60; "
                               "if(b.a>=60) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=60"))
        self.assertTrue(any(r.expression == "60" and "explicit_alias_candidate" in r.uncertainty for r in rows))
        project = self.project("int F(void) { State *p; if(p->a>=60) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "p->a", "p->a>=60"))
        self.assertTrue(any("pointer_target_not_resolved" in r.uncertainty for r in rows))
        self.assertFalse(any(r.kind == "ct_global_input" for r in rows))

    def test_struct_and_pointer_return_projections_keep_member_path(self):
        project = self.project("static State stored={.a=60}; State Get(void) { return stored; } "
                               "State *GetPtr(void) { return &stored; } "
                               "int F(void) { State b=Get(); State *p=GetPtr(); if (b.a && p->a) return 1; return 0; }")
        for expression in ("b.a", "p->a"):
            rows = project.value_resolver.sources(self.probe(project, "F", expression, "b.a && p->a"))
            returned = next(r for r in rows if r.kind == "return_value")
            sources = project.value_resolver.sources(returned.next_probe)
            member = next(r for r in sources if r.next_probe)
            self.assertEqual(member.next_probe.expression, "stored.a")
            initialized = project.value_resolver.sources(member.next_probe)
            self.assertIn("60", [r.expression for r in initialized if r.kind == "constant"])

    def test_whole_struct_and_member_rte_outputs_reach_the_right_producer_field(self):
        project = self.project("void Supply(void) { State src; src.a=60; Rte_Write_State(&src); Rte_Write_Field(src.a); } "
                               "int F(void) { State b; Rte_Read_State(&b); if (b.a>=60) return 1; return 0; } "
                               "int G(void) { State b; Rte_Read_Field(&b.a); if (b.a>=60) return 1; return 0; }")
        for name in ("F", "G"):
            rows = project.value_resolver.sources(self.probe(project, name, "b.a", "b.a>=60"))
            rte = next(r for r in rows if r.kind == "rte_data")
            self.assertEqual(rte.next_probe.expression, "src.a")
            self.assertIn("name_only_connection", rte.uncertainty)
            self.assertIn("60", [r.expression for r in project.value_resolver.sources(rte.next_probe)])

    def test_function_output_and_pointer_parameter_bind_to_caller_object(self):
        project = self.project("void Fill(State *out) { out->a=60; } "
                               "int F(void) { State b; Fill(&b); if (b.a>=60) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=60"))
        output = next(r for r in rows if r.kind == "output_parameter")
        self.assertEqual(output.next_probe.expression, "out->a")
        values = project.value_resolver.sources(output.next_probe)
        self.assertIn("60", [r.expression for r in values if r.kind == "constant"])
        caller = next(r for r in values if r.kind == "parameter_input")
        self.assertEqual(caller.next_probe.expression, "b.a")
        self.assertIn("call_context_not_bound", caller.uncertainty)

    def test_scalar_output_to_struct_member_and_dereferenced_whole_object_copy(self):
        project = self.project("void Set(unsigned *out) { *out=60; } "
                               "int F(void) { State b; State other={.a=22}; State *p=&b; *p=other; Set(&b.a); "
                               "if (b.a>=60) return 1; return 0; }")
        rows = project.value_resolver.sources(self.probe(project, "F", "b.a", "b.a>=60"))
        self.assertIn("other.a", [r.next_probe.expression for r in rows if r.next_probe])
        out = next(r for r in rows if r.kind == "output_parameter")
        self.assertEqual(out.next_probe.expression, "*out")
        self.assertIn("60", [r.expression for r in project.value_resolver.sources(out.next_probe)])

    def test_global_member_writes_cross_files_but_static_and_local_names_are_excluded(self):
        (self.folder / "state.h").write_text(TYPE + "extern State shared;", encoding="utf-8")
        (self.folder / "use.c").write_text('#include "state.h"\nint Use(void) { if(shared.a>=60) return 1; return 0; }', encoding="utf-8")
        (self.folder / "write.c").write_text('#include "state.h"\nState shared; void Write(void) { shared.a=60; }', encoding="utf-8")
        (self.folder / "private.c").write_text(TYPE + "static State shared; void Private(void) { shared.a=99; }", encoding="utf-8")
        (self.folder / "shadow.c").write_text(TYPE + "void Shadow(void) { State shared; shared.a=88; }", encoding="utf-8")
        project = analyze_project(self.folder)
        rows = project.value_resolver.sources(self.probe(project, "Use", "shared.a", "shared.a>=60"))
        writes = [r for r in rows if r.kind == "constant"]
        self.assertEqual([r.expression for r in writes], ["60"])
        self.assertIn("global_linkage_not_proven", writes[0].uncertainty)
        root = next(r for r in rows if r.kind == "object_origin")
        self.assertTrue(any(r.kind == "ct_global_input" for r in project.value_resolver.sources(root.next_probe)))

    def test_member_goal_and_projected_return_restore_in_sqlite(self):
        project = self.project("State Make(void) { State b={.a=60}; return b; } "
                               "int F(void) { State b=Make(); if(b.a>=60) return 1; return 0; }")
        workbench = Workbench()
        workbench.project = project
        fn = project.functions_by_name["F"][0]
        branch = next(b for r in project.results for b in r.branches if b.function_id == fn.id)
        workbench.start(fn.id, branch.id, "구조체 목표")
        workbench.set_variable_goal("b.a", "60", branch.location)
        row = next(r for r in workbench.value_candidates() if r.value_kind == "return_value")
        workbench.follow(row, "구조체 반환의 같은 멤버 조사")
        database = self.folder / "members.sqlite3"
        workbench.save(database)
        with closing(sqlite3.connect(database)) as connection:
            payload = json.loads(connection.execute("SELECT payload FROM trace_sessions").fetchone()[0])
            self.assertEqual(payload["format_version"], 3)
        restored = Workbench()
        restored.restore(database, workbench.session.id)
        self.assertEqual(restored.session, workbench.session)
        self.assertEqual(restored.manager.current_step.probe.expression, "$return.a")
        self.assertEqual(restored.session.variable_goal.variable, "b.a")

    def test_pointer_object_origin_does_not_turn_into_confirmed_pointee_control(self):
        project = self.project("State *shared; int F(void) { if(shared->a>=60) return 1; return 0; }")
        workbench = Workbench()
        workbench.project = project
        fn = project.functions_by_name["F"][0]
        branch = project.results[0].branches[0]
        workbench.start(fn.id, branch.id, "포인터 대상 확인")
        workbench.set_variable_goal("shared->a", "60", branch.location)
        workbench.follow(next(c for c in workbench.value_candidates() if c.value_kind == "object_origin"), "포인터 값 출처")
        boundary = next(c for c in workbench.value_candidates() if c.value_kind == "ct_global_input")
        self.assertIn("pointer_value_not_pointee_control", boundary.uncertainty)
        self.assertEqual(workbench.session.variable_goal.variable, "shared->a")


if __name__ == "__main__":
    unittest.main()
