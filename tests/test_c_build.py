"""Host compiler selection tests for the synthetic C execution fixtures."""

import sys
import unittest
from unittest.mock import patch

from c_build import compiler_command


class CompilerSelectionTests(unittest.TestCase):
    def test_macos_prefers_system_clang_over_installed_zig_package(self):
        with patch.object(sys, "platform", "darwin"), \
                patch("c_build.shutil.which", side_effect=lambda name: "/usr/bin/clang" if name == "clang" else None), \
                patch("c_build.importlib.util.find_spec") as find_spec:
            self.assertEqual(compiler_command(), ["/usr/bin/clang"])
        find_spec.assert_not_called()

    def test_other_platforms_keep_using_installed_zig_package(self):
        with patch.object(sys, "platform", "win32"), \
                patch("c_build.importlib.util.find_spec", return_value=object()):
            self.assertEqual(compiler_command(), [sys.executable, "-m", "ziglang", "cc"])


if __name__ == "__main__":
    unittest.main()
