"""RTE names are candidate evidence, not proven deployment wiring."""

from pathlib import Path
import unittest

from autosar_trace_navigator.parser import parse_source
from autosar_trace_navigator.rte import inspect_rte_header, resolve_rte


BASE = Path(__file__).resolve().parents[1] / "test" / "virtual_rte"


def source(text: str, name: str = "component.c"):
    """Parse synthetic bytes with an explicit virtual source path."""
    return parse_source(text.encode(), path=BASE / name)


class RteTests(unittest.TestCase):
    def test_read_write_links_use_complete_suffix_and_keep_call_model(self):
        parsed = source("void Consumer(void) { Rte_Read_Vehicle_Speed_Raw(&x); }\n"
                        "void Producer(void) { Rte_Write_Vehicle_Speed_Raw(x); }")
        header = inspect_rte_header(
            b"int Rte_Read_Vehicle_Speed_Raw(int *x);\nint Rte_Write_Vehicle_Speed_Raw(int x);",
            path=BASE / "Rte_Component.h")
        original_calls = parsed.calls
        result = resolve_rte((parsed,), headers=(header,))
        self.assertEqual([a.direction for a in result.accesses], ["read", "write"])
        self.assertEqual(len(result.dependencies), 1)
        relation = result.dependencies[0]
        self.assertEqual(relation.channel, "Vehicle_Speed_Raw")
        self.assertEqual(relation.consumer_access_id, result.accesses[0].id)
        self.assertEqual(relation.producer_access_id, result.accesses[1].id)
        self.assertIn("name_only_connection", relation.uncertainty)
        self.assertTrue(all(a.header_locations for a in result.accesses))
        self.assertEqual(parsed.calls, original_calls)
        self.assertFalse(result.diagnostics)

    def test_missing_producer_and_header_are_explicit(self):
        result = resolve_rte((source("void f(void) { Rte_Read_Speed_Raw(&x); }"),))
        self.assertEqual(result.dependencies, ())
        self.assertEqual({d.code for d in result.diagnostics},
                         {"MISSING_HEADER_API", "NO_PRODUCER_CANDIDATE"})
        self.assertIn("missing_header_declaration", result.accesses[0].uncertainty)

    def test_multiple_producers_remain_distinct_and_marked(self):
        parsed = source("void A(void) { Rte_Write_Speed_Raw(x); }\n"
                        "void B(void) { Rte_Write_Speed_Raw(y); }\n"
                        "void C(void) { Rte_Read_Speed_Raw(&x); }")
        result = resolve_rte((parsed,))
        self.assertEqual(len(result.dependencies), 2)
        self.assertTrue(all("multiple_producer_candidates" in d.uncertainty for d in result.dependencies))
        self.assertIn("MULTIPLE_PRODUCER_CANDIDATES", {d.code for d in result.diagnostics})

    def test_similar_names_do_not_create_false_suffix_matches(self):
        result = resolve_rte((source("void f(void) { Rte_Read_Speed_Raw(&x); "
                                     "Rte_Write_Speed_RawBackup(x); Rte_Write_speed_Raw(x); }"),))
        self.assertEqual(len(result.accesses), 3)
        self.assertEqual(result.dependencies, ())

    def test_header_macros_keep_text_and_unexpanded_uncertainty(self):
        header = inspect_rte_header(
            b"#define Rte_Read_Speed_Raw(p) Internal_Read(p)\n"
            b"#define Rte_Write_Speed_Raw HiddenWriter\n", path=BASE / "Rte_Macros.h")
        self.assertEqual([a.form for a in header.apis], ["macro", "macro"])
        self.assertIn("Internal_Read", header.apis[0].expression)
        parsed = source("void f(void) { Rte_Read_Speed_Raw(&x); Rte_Write_Speed_Raw(x); }")
        result = resolve_rte((parsed,), headers=(header,))
        self.assertEqual(len(result.dependencies), 1)
        self.assertIn("header_macro_not_expanded", result.dependencies[0].uncertainty)
        self.assertEqual(len(parsed.calls), 2)  # Internal_Read is not invented as a call.

    def test_duplicate_header_api_is_ambiguous_even_in_different_components(self):
        headers = tuple(inspect_rte_header(b"int Rte_Read_Speed_Raw(int *p);", path=BASE / name)
                        for name in ("Rte_A.h", "Rte_B.h"))
        result = resolve_rte((source("void f(void) { Rte_Read_Speed_Raw(&x); }"),), headers=headers)
        self.assertEqual(len(result.accesses[0].header_locations), 2)
        self.assertIn("multiple_header_candidates", result.accesses[0].uncertainty)
        self.assertIn("AMBIGUOUS_HEADER_API", {d.code for d in result.diagnostics})

    def test_implicit_client_server_and_indirect_forms_are_not_guessed(self):
        parsed = source("void f(void) { Rte_IRead_Run_Speed_Raw(); Rte_Call_Port_Op(); "
                        "(*Rte_Read_Speed_Raw)(&x); Rte_Read_(); Ordinary(); }")
        result = resolve_rte((parsed,))
        self.assertEqual(result.accesses, ())
        self.assertEqual(len(result.diagnostics), 4)
        self.assertTrue(all(d.code == "UNSUPPORTED_RTE_API" for d in result.diagnostics))

    def test_conditional_producers_are_not_pruned(self):
        parsed = source("#if FEATURE\nvoid A(void) { Rte_Write_Speed_Raw(x); }\n"
                        "#else\nvoid A(void) { Rte_Write_Speed_Raw(y); }\n#endif\n"
                        "void B(void) { Rte_Read_Speed_Raw(&x); }")
        result = resolve_rte((parsed,))
        self.assertEqual(len(result.dependencies), 2)
        self.assertTrue(all("preprocessing_not_performed" in d.uncertainty for d in result.dependencies))

    def test_invalid_header_and_unknown_owner_are_not_clean_results(self):
        header = inspect_rte_header(b"int Rte_Read_Speed_Raw(int *p", path=BASE / "Rte_Broken.h")
        self.assertIn("HEADER_SYNTAX_ERROR", {d.code for d in header.diagnostics})
        parsed = source("int x = Rte_Read_Speed_Raw(0);")
        result = resolve_rte((parsed,), headers=(header,))
        self.assertIsNone(result.accesses[0].function_id)
        self.assertIn("UNKNOWN_ACCESS_OWNER", {d.code for d in result.diagnostics})

    def test_duplicate_inputs_rejected_and_result_order_deterministic(self):
        first = source("void f(void) { Rte_Read_X(&x); }", "a.c")
        second = source("void g(void) { Rte_Write_X(x); }", "b.c")
        self.assertEqual(resolve_rte((first, second)), resolve_rte((second, first)))
        with self.assertRaises(ValueError):
            resolve_rte((first, first))
        header = inspect_rte_header(b"", path=BASE / "Rte_Empty.h")
        with self.assertRaises(ValueError):
            resolve_rte((), headers=(header, header))
        self.assertEqual(resolve_rte(()).accesses, ())


if __name__ == "__main__":
    unittest.main()
