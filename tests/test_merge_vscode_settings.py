"""Unit tests for scripts/merge_vscode_settings.py (pure Python, no bash needed)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "merge_vscode_settings.py"
FRAGMENT = ROOT / ".config/Code/User/settings.json"
OVERLAY = json.loads(FRAGMENT.read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("merge_vscode_settings", SCRIPT)
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)


class MergeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="merge-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True)

    def write(self, name, content, raw_bytes=False):
        target = self.base / name
        if raw_bytes:
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        return target

    def merge_via_cli(self, dest):
        output = self.base / "out.json"
        result = self.run_cli(str(FRAGMENT), str(dest), "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        return output.read_text(encoding="utf-8")

    def test_zero_byte_file_merges_as_empty_object(self):
        dest = self.write("settings.json", "")
        merged = self.merge_via_cli(dest)
        self.assertEqual(json.loads(merged), OVERLAY)
        self.assertEqual(self.run_cli(str(FRAGMENT), str(dest), "--check").stdout.strip(), "changed")
        dest.write_text(merged, encoding="utf-8")
        self.assertEqual(self.run_cli(str(FRAGMENT), str(dest), "--check").stdout.strip(), "unchanged")

    def test_whitespace_only_file_merges_as_empty_object(self):
        merged = merge.merge_settings("  \n\t\n", OVERLAY)
        self.assertEqual(merge.parse_jsonc(merged)[2], OVERLAY)
        self.assertNotIn("\t", merged)

    def test_bom_file_is_read_and_rewritten_without_bom(self):
        payload = b'\xef\xbb\xbf{"editor.fontSize": 18, "editor.cursorStyle": "line"}\n'
        dest = self.write("settings.json", payload, raw_bytes=True)
        merged = self.merge_via_cli(dest)
        self.assertFalse(merged.encode("utf-8").startswith(b"\xef\xbb\xbf"))
        value = json.loads(merged)
        self.assertEqual(value["editor.fontSize"], 18)
        self.assertEqual(value["editor.cursorStyle"], "block")

    def test_comment_only_file_keeps_comments_before_merged_object(self):
        text = "// Personal settings.\n/* block */\n"
        merged = merge.merge_settings(text, OVERLAY)
        self.assertTrue(merged.startswith("// Personal settings."))
        self.assertLess(merged.index("/* block */"), merged.index("{"))
        self.assertEqual(merge.parse_jsonc(merged)[2], OVERLAY)

    def test_comment_only_file_without_trailing_newline(self):
        merged = merge.merge_settings("// no newline", OVERLAY)
        self.assertTrue(merged.startswith("// no newline"))
        self.assertEqual(merge.parse_jsonc(merged)[2], OVERLAY)

    def test_merge_is_idempotent_for_comment_only_file(self):
        first = merge.merge_settings("// Personal settings.\n", OVERLAY)
        self.assertEqual(merge.merge_settings(first, OVERLAY), first)

    def test_comments_and_trailing_commas_are_preserved(self):
        text = '''{
    // Keep personal settings and their comments.
    "editor.fontSize": 18,
    "custom.url": "https://example.invalid/path/, }",
    "editor.cursorStyle": "line", // Replace only its value.
    "workbench.colorCustomizations": {
        "statusBar.background": "#123456",
        "editorCursor.foreground": "#FFFFFF",
    },
}
'''
        merged = merge.merge_settings(text, OVERLAY)
        self.assertIn('// Keep personal settings and their comments.', merged)
        self.assertIn('// Replace only its value.', merged)
        self.assertIn('"editor.fontSize": 18', merged)
        self.assertIn('"editor.cursorStyle": "block"', merged)
        self.assertIn('https://example.invalid/path/, }', merged)
        self.assertEqual(merge.merge_settings(merged, OVERLAY), merged)

    def test_single_line_object_appends_with_valid_commas(self):
        # `}` 紧跟末成员值：逗号插入与新增键插入曾落同一偏移点而破坏 JSON。
        text = '{"editor.cursorStyle": "line"}'
        merged = merge.merge_settings(text, OVERLAY)
        self.assertEqual(merge.parse_jsonc(merged)[2], OVERLAY)
        self.assertEqual(merge.merge_settings(merged, OVERLAY), merged)

    def test_nested_dict_partial_merge(self):
        text = '''{
    "workbench.colorCustomizations": {
        "statusBar.background": "#123456"
    }
}
'''
        merged = merge.merge_settings(text, OVERLAY)
        value = merge.parse_jsonc(merged)[2]
        colors = value["workbench.colorCustomizations"]
        self.assertEqual(colors["statusBar.background"], "#123456")
        self.assertEqual(colors["editorCursor.foreground"], "#FEDFE1")
        self.assertEqual(colors["terminalCursor.background"], "#1E1E2E")

    def test_invalid_json_still_fails(self):
        with self.assertRaises(ValueError):
            merge.merge_settings("{invalid settings", OVERLAY)
        dest = self.write("settings.json", "{invalid settings")
        result = self.run_cli(str(FRAGMENT), str(dest), "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot merge VS Code settings", result.stderr)
        self.assertEqual(dest.read_text(encoding="utf-8"), "{invalid settings")

    def test_non_object_json_still_fails(self):
        for text in ('"foo"', "42", "[1, 2]"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    merge.merge_settings(text, OVERLAY)


if __name__ == "__main__":
    unittest.main()
