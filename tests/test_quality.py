from __future__ import annotations

import shutil
import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY_SPEC = spec_from_file_location("quality", ROOT / "scripts" / "quality.py")
assert QUALITY_SPEC is not None and QUALITY_SPEC.loader is not None
quality = module_from_spec(QUALITY_SPEC)
QUALITY_SPEC.loader.exec_module(quality)


class RepositoryQualityTests(unittest.TestCase):
    def test_fomod_has_the_three_exact_exclusive_choices_and_no_payload(self) -> None:
        self.assertEqual(quality.fomod_issues(), [])

    def test_all_xml_and_text_files_pass_hygiene(self) -> None:
        self.assertEqual(quality.hygiene_issues(), [])

    def test_workflow_and_python_dependencies_are_pinned(self) -> None:
        self.assertEqual(quality.pin_issues(), [])

    def test_fomod_rejects_unvalidated_payload_files(self) -> None:
        original = quality.ROOT
        try:
            with tempfile.TemporaryDirectory() as temporary:
                temporary_root = Path(temporary)
                shutil.copytree(original / "fomod", temporary_root / "fomod")
                (temporary_root / "fomod" / "files").mkdir()
                quality.ROOT = temporary_root
                issues = quality.fomod_issues()
        finally:
            quality.ROOT = original
        self.assertIn(
            "FOMOD payload directory must not exist before native gift behavior is validated",
            issues,
        )

    def test_hygiene_detects_trailing_whitespace_and_missing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.txt"
            path.write_bytes(b"bad \nlast")
            issues = quality.hygiene_issues([path])
        self.assertTrue(any("trailing whitespace" in issue for issue in issues))
        self.assertTrue(any("missing final newline" in issue for issue in issues))

    def test_policy_rejects_hook_bypasses_and_inline_suppressions(self) -> None:
        original = quality.ROOT
        try:
            with tempfile.TemporaryDirectory() as temporary:
                temporary_root = Path(temporary)
                (temporary_root / "automation.sh").write_text(
                    "git commit " + "-" * 2 + "no-verify\n", encoding="utf-8"
                )
                (temporary_root / "source.py").write_text("# " + "noqa" + "\n", encoding="utf-8")
                quality.ROOT = temporary_root
                issues = quality.policy_issues()
        finally:
            quality.ROOT = original
        self.assertEqual(len(issues), 2)
        self.assertTrue(any("hook-bypass" in issue for issue in issues))
        self.assertTrue(any("suppression" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
