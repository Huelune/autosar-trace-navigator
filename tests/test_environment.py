"""STEP 1 integration checks for the installed local environment."""

import importlib.metadata
from contextlib import closing
import sqlite3
import tkinter
import unittest

from tree_sitter import Language, Parser
import tree_sitter_c

import autosar_trace_navigator


class EnvironmentTests(unittest.TestCase):
    def test_installed_package_version(self):
        self.assertEqual(
            importlib.metadata.version("autosar-trace-navigator"),
            autosar_trace_navigator.__version__,
        )

    def test_c_grammar_loads_and_parses(self):
        parser = Parser(Language(tree_sitter_c.language()))
        tree = parser.parse(b"int main(void) { return 0; }")
        self.assertFalse(tree.root_node.has_error)
        self.assertEqual(tree.root_node.named_children[0].type, "function_definition")

    def test_sqlite_local_storage_available(self):
        with closing(sqlite3.connect(":memory:")) as connection:
            self.assertEqual(connection.execute("SELECT 1").fetchone(), (1,))

    def test_tcl_runtime_available_without_gui(self):
        interpreter = tkinter.Tcl()
        self.assertTrue(interpreter.call("info", "patchlevel"))


if __name__ == "__main__":
    unittest.main()
