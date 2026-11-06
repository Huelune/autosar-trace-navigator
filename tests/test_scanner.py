"""Scanner contracts, including a read-only scan of the AUTOSAR sample."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autosar_trace_navigator.scanner import scan_sources


ROOT = Path(__file__).resolve().parents[1]


class ScannerTests(unittest.TestCase):
    def setUp(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="scanner-", dir=build)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def write(self, name: str, content: str = "/* synthetic C */\n") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_nested_extensions_rte_and_stable_paths(self):
        for name in ("src/main.c", "include/types.H", "generated/Rte_Brake.h",
                     "nested/deep/upper.C", "README.md", "ignore.cpp", "ignore.c.bak"):
            self.write(name)
        result = scan_sources(self.root)
        self.assertEqual([item.relative_path.as_posix() for item in result], [
            "generated/Rte_Brake.h", "include/types.H", "nested/deep/upper.C", "src/main.c",
        ])
        self.assertEqual(result, scan_sources(self.root))
        self.assertEqual([item.is_rte_header for item in result], [True, False, False, False])
        for item in result:
            self.assertTrue(item.path.is_absolute())
            self.assertEqual(item.path, self.root / item.relative_path)

    def test_exclude_file_and_directory_without_prefix_collisions(self):
        for name in ("src/keep.c", "src/drop.c", "generated/Rte_A.h", "generated2/keep.h"):
            self.write(name)
        result = scan_sources(self.root, exclude_paths=("generated", self.root / "src/drop.c"))
        self.assertEqual([item.relative_path.as_posix() for item in result],
                         ["generated2/keep.h", "src/keep.c"])

    def test_exclusion_is_root_relative_not_working_directory_relative(self):
        self.write("src/main.c")
        self.assertEqual(scan_sources(self.root, exclude_paths=("src",)), ())

    def test_exclude_entire_root_or_nonexistent_path(self):
        self.write("main.c")
        self.assertEqual(scan_sources(self.root, exclude_paths=(".",)), ())
        self.assertEqual(len(scan_sources(self.root, exclude_paths=("missing",))), 1)

    def test_outside_exclusion_is_rejected(self):
        with self.assertRaises(ValueError):
            scan_sources(self.root, exclude_paths=("../outside",))

    def test_empty_directory_and_missing_root_and_file_root(self):
        self.assertEqual(scan_sources(self.root), ())
        with self.assertRaises(FileNotFoundError):
            scan_sources(self.root / "missing")
        with self.assertRaises(NotADirectoryError):
            scan_sources(self.write("main.c"))

    def test_unicode_and_spaces(self):
        self.write("가상 코드/속도 판단.c")
        self.assertEqual(scan_sources(self.root)[0].relative_path,
                         Path("가상 코드/속도 판단.c"))

    def test_directory_read_errors_are_not_silently_ignored(self):
        with patch("autosar_trace_navigator.scanner.os.scandir", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                scan_sources(self.root)

    def test_excluded_directory_is_not_traversed(self):
        self.write("excluded/private.c")
        self.write("keep.c")
        from os import scandir

        def guarded_scandir(path):
            self.assertNotEqual(Path(path), self.root / "excluded")
            return scandir(path)

        with patch("autosar_trace_navigator.scanner.os.scandir", side_effect=guarded_scandir):
            self.assertEqual(len(scan_sources(self.root, exclude_paths=("excluded",))), 1)

    def test_link_entries_are_not_traversed_or_returned(self):
        self.write("real/keep.c")
        self.write("alias.c")
        (self.root / "alias_dir").mkdir()
        # Model link classification without requiring Windows symlink privileges.
        with patch("autosar_trace_navigator.scanner._is_link",
                   side_effect=lambda path: path.name in {"alias.c", "alias_dir"}):
            self.assertEqual([item.relative_path.as_posix() for item in scan_sources(self.root)],
                             ["real/keep.c"])

    def test_autosar_sample_expected_files_and_no_source_changes(self):
        sample = ROOT / "test"

        def snapshot():
            return {
                path.relative_to(sample): (hashlib.sha256(path.read_bytes()).hexdigest(),
                                          path.stat().st_mtime_ns)
                for path in sample.rglob("*") if path.is_file()
            }

        before = snapshot()
        result = scan_sources(sample, include_paths=("include", "src", "support"))
        self.assertEqual({item.relative_path.as_posix() for item in result}, {
            "include/BrakeControl.h", "include/Rte_BrakeControl.h",
            "include/Rte_SensorAcquisition.h", "include/Std_Types.h",
            "include/TestPlatform.h", "src/AssistDecision.c", "src/BrakeControl.c",
            "src/SensorAcquisition.c", "src/SpeedSignal.c", "support/Rte_Stub.c",
            "support/test_brake_control.c",
        })
        self.assertEqual(sum(item.is_rte_header for item in result), 2)
        self.assertEqual(before, snapshot())


if __name__ == "__main__":
    unittest.main()
