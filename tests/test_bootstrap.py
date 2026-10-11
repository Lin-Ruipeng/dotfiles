"""Regression checks use disposable configuration sources and HOME directories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "source repo"
        self.home = self.base / "home"
        self.bin = self.base / "bin"
        for directory in (self.repo, self.home, self.bin):
            directory.mkdir()
        for name in ("bootstrap.sh", ".zshrc", ".vimrc", ".wslconfig",
                     ".config/ghostty/config", ".config/zed/settings.json",
                     ".config/Code/User/settings.json", "scripts/merge_vscode_settings.py"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.env = os.environ.copy()
        for name in ("ZSH_CUSTOM", "ZDOTDIR", "BASH_ENV", "ENV"):
            self.env.pop(name, None)
        self.env.update(HOME=str(self.home), DISPLAY="", WAYLAND_DISPLAY="",
                        XDG_CONFIG_HOME="", PATH=f"{self.bin}:/usr/bin:/bin",
                        TEST_WSL="0")
        self.command("grep", '''if [ "$*" = "-qi microsoft /proc/version" ]; then
  [ "$TEST_WSL" = 1 ]
else
  exec /usr/bin/grep "$@"
fi
''')

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)

    def run_bootstrap(self, *args, success=True):
        result = subprocess.run(
            ["/bin/bash", str(self.repo / "bootstrap.sh"), *args],
            env=self.env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def backups(self):
        root = self.home / ".dotfiles-backup"
        return sorted(root.iterdir()) if root.exists() else []

    def saved(self, backup, target, category="files"):
        return backup / category / str(target).lstrip("/")

    def snapshot(self):
        result = {}
        for path in self.home.rglob("*"):
            key = str(path.relative_to(self.home))
            if path.is_symlink():
                result[key] = ("link", os.readlink(path))
            elif path.is_file():
                result[key] = ("file", path.read_bytes(), path.stat().st_mode)
            else:
                result[key] = ("directory",)
        return result

    def graphical(self):
        self.env.update(DISPLAY=":0", WAYLAND_DISPLAY="wayland-0")

    def windows(self):
        win_home = self.base / "Windows User"
        win_home.mkdir()
        self.env.update(TEST_WSL="1", TEST_WIN_HOME=str(win_home))
        self.command("cmd.exe", "printf '%s\\r\\n' 'C:\\Users\\Test User'\n")
        self.command("wslpath", 'printf "%s\\n" "$TEST_WIN_HOME"\n')
        return win_home

    def test_independent_copies_and_idempotency(self):
        self.run_bootstrap()
        before = self.snapshot()
        self.run_bootstrap()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.backups(), [])
        self.repo.rename(self.base / "source unavailable")
        for name in (".zshrc", ".vimrc"):
            target = self.home / name
            self.assertFalse(target.is_symlink())
            self.assertTrue(target.read_text())
        if shutil.which("zsh"):
            result = self.zsh('source "$HOME/.zshrc"; print shell-started')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("shell-started", result.stdout)

    def test_same_content_link_is_still_materialized(self):
        target = self.home / ".zshrc"
        target.symlink_to(self.repo / ".zshrc")
        self.run_bootstrap()
        self.assertFalse(target.is_symlink())
        saved = self.saved(self.backups()[0], target)
        self.repo.rename(self.base / "source unavailable")
        self.assertFalse(saved.is_symlink())
        self.assertEqual(saved.read_bytes(), target.read_bytes())

    def test_legacy_backup_survives_source_removal(self):
        legacy = self.base / "legacy"
        legacy.mkdir()
        (legacy / ".zshrc").write_text("legacy-settings\n")
        target = self.home / ".zshrc"
        target.symlink_to(legacy / ".zshrc")
        self.run_bootstrap()
        legacy.rename(self.base / "legacy unavailable")
        self.assertEqual(self.saved(self.backups()[0], target).read_text(), "legacy-settings\n")

    def test_dangling_file_link_is_recorded_and_replaced(self):
        target = self.home / ".vimrc"
        target.symlink_to("missing-vimrc")
        self.run_bootstrap()
        record = self.saved(self.backups()[0] / "links", target)
        self.assertEqual(Path(str(record) + ".target").read_text(), "missing-vimrc\n")
        self.assertFalse(target.is_symlink())
        self.assertTrue(target.is_file())

    def test_directory_link_preserves_extras_and_independent_backup(self):
        self.graphical()
        legacy = self.base / "legacy ghostty"
        legacy.mkdir()
        (legacy / "config").write_text("local-ghostty\n")
        (legacy / "extra").write_text("extra-settings\n")
        (self.home / ".config").mkdir()
        target = self.home / ".config/ghostty"
        target.symlink_to(legacy, target_is_directory=True)
        self.run_bootstrap()
        legacy.rename(self.base / "legacy unavailable")
        self.assertFalse(target.is_symlink())
        self.assertEqual((target / "extra").read_text(), "extra-settings\n")
        saved = self.saved(self.backups()[0], target, "directories")
        self.assertEqual((saved / "config").read_text(), "local-ghostty\n")
        self.assertEqual((saved / "extra").read_text(), "extra-settings\n")

    def test_parent_directory_link_is_also_materialized(self):
        self.graphical()
        legacy = self.base / "legacy config"
        (legacy / "ghostty").mkdir(parents=True)
        shutil.copyfile(self.repo / ".config/ghostty/config", legacy / "ghostty/config")
        (legacy / "unmanaged").write_text("keep\n")
        (self.home / ".config").symlink_to(legacy, target_is_directory=True)
        self.run_bootstrap()
        legacy.rename(self.base / "legacy unavailable")
        self.assertFalse((self.home / ".config").is_symlink())
        self.assertEqual((self.home / ".config/unmanaged").read_text(), "keep\n")

    def test_dangling_directory_link_is_materialized(self):
        self.graphical()
        (self.home / ".config").mkdir()
        target = self.home / ".config/ghostty"
        target.symlink_to("missing-directory", target_is_directory=True)
        self.run_bootstrap()
        self.assertFalse(target.is_symlink())
        self.assertTrue((target / "config").is_file())

    def test_same_second_backups_do_not_overwrite(self):
        self.command("date", "printf '20000101-000000\\n'\n")
        target = self.home / ".zshrc"
        target.write_text("first\n")
        self.run_bootstrap()
        target.write_text("second\n")
        self.run_bootstrap()
        backups = self.backups()
        self.assertEqual(len(backups), 2)
        self.assertEqual({self.saved(b, target).read_text() for b in backups},
                         {"first\n", "second\n"})

    def test_dry_run_changes_nothing_including_links(self):
        self.graphical()
        (self.home / ".zshrc").symlink_to(self.repo / ".zshrc")
        (self.home / ".vimrc").write_text("user-vim\n")
        before = self.snapshot()
        output = self.run_bootstrap("--dry-run").stdout
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.backups(), [])
        self.assertIn("将复制为独立文件", output)
        self.assertNotIn("✓ 已复制", output)

    def test_missing_source_fails_before_any_changes(self):
        self.graphical()
        (self.home / ".zshrc").write_text("keep\n")
        (self.repo / ".config/zed/settings.json").unlink()
        before = self.snapshot()
        self.run_bootstrap(success=False)
        self.assertEqual(before, self.snapshot())

    def test_file_in_place_of_directory_fails_preflight(self):
        self.graphical()
        (self.home / ".config").write_text("keep\n")
        before = self.snapshot()
        self.run_bootstrap(success=False)
        self.assertEqual(before, self.snapshot())

    def test_copy_failure_preserves_original_and_cleans_stage(self):
        target = self.home / ".zshrc"
        target.write_text("keep\n")
        self.command("cp", '''for arg do
  case "$arg" in *'.dotfiles-file.'*) exit 42 ;; esac
done
exec /bin/cp "$@"
''')
        self.run_bootstrap(success=False)
        self.assertEqual(target.read_text(), "keep\n")
        self.assertEqual(list(self.home.glob(".dotfiles-file.*")), [])

    def test_file_rename_failure_preserves_original(self):
        target = self.home / ".zshrc"
        target.write_text("keep\n")
        self.command("mv", '''for arg do
  case "$arg" in *'.dotfiles-file.'*) exit 42 ;; esac
done
exec /bin/mv "$@"
''')
        self.run_bootstrap(success=False)
        self.assertEqual(target.read_text(), "keep\n")
        self.assertEqual(self.saved(self.backups()[0], target).read_text(), "keep\n")
        self.assertEqual(list(self.home.glob(".dotfiles-file.*")), [])

    def test_directory_rename_failure_restores_original_link(self):
        self.graphical()
        legacy = self.base / "legacy"
        legacy.mkdir()
        (legacy / "config").write_text("keep\n")
        (self.home / ".config").mkdir()
        target = self.home / ".config/ghostty"
        target.symlink_to(legacy, target_is_directory=True)
        self.command("mv", '''for arg do
  case "$arg" in *'.dotfiles-directory.'*) exit 42 ;; esac
done
exec /bin/mv "$@"
''')
        self.run_bootstrap(success=False)
        self.assertTrue(target.is_symlink())
        self.assertEqual((target / "config").read_text(), "keep\n")
        self.assertEqual(list(target.parent.glob(".dotfiles-*")), [])

    def test_headless_skips_desktop_configs_and_dependencies(self):
        output = self.run_bootstrap().stdout
        self.assertFalse((self.home / ".config").exists())
        for hint in ("✗ zed", "✗ ghostty", "✗ code", "✗ python3", "✗ wl-copy", "✗ xclip", "✗ 字体"):
            self.assertNotIn(hint, output)

    def test_graphical_deployment_preserves_extra_zed_files(self):
        self.graphical()
        extra = self.home / ".config/zed/themes/user.json"
        extra.parent.mkdir(parents=True)
        extra.write_text("{}\n")
        self.run_bootstrap()
        self.assertTrue((self.home / ".config/ghostty/config").is_file())
        self.assertTrue((self.home / ".config/zed/settings.json").is_file())
        self.assertTrue((self.home / ".config/Code/User/settings.json").is_file())
        self.assertEqual(extra.read_text(), "{}\n")
        self.repo.rename(self.base / "source unavailable")
        self.assertTrue((self.home / ".config/zed/settings.json").read_text())

    def test_skip_zed_preserves_existing_settings(self):
        self.graphical()
        target = self.home / ".config/zed/settings.json"
        target.parent.mkdir(parents=True)
        target.write_text("user-specific-settings\n")
        (self.repo / ".config/zed/settings.json").unlink()
        output = self.run_bootstrap("--skip-zed").stdout
        self.assertEqual(target.read_text(), "user-specific-settings\n")
        self.assertNotIn("✗ zed", output)

    def test_custom_config_home(self):
        self.graphical()
        config_home = self.home / "custom config"
        self.env["XDG_CONFIG_HOME"] = str(config_home)
        self.run_bootstrap()
        self.assertTrue((config_home / "zed/settings.json").is_file())
        self.assertTrue((config_home / "ghostty/config").is_file())
        self.assertTrue((config_home / "Code/User/settings.json").is_file())
        self.assertFalse((self.home / ".config").exists())

    def test_relative_config_home_is_rejected(self):
        self.env["XDG_CONFIG_HOME"] = "relative"
        self.run_bootstrap(success=False)
        self.assertEqual(self.snapshot(), {})

    def test_wslg_deploys_zed_and_windows_config_but_not_ghostty(self):
        self.graphical()
        windows_home = self.windows()
        target = windows_home / ".wslconfig"
        target.write_text("old-wsl-settings\n")
        output = self.run_bootstrap().stdout
        self.assertTrue((self.home / ".config/zed/settings.json").is_file())
        self.assertTrue((self.home / ".config/Code/User/settings.json").is_file())
        self.assertFalse((self.home / ".config/ghostty").exists())
        self.assertEqual(target.read_bytes(), (self.repo / ".wslconfig").read_bytes())
        self.assertEqual(self.saved(self.backups()[0], target).read_text(), "old-wsl-settings\n")
        self.assertIn("手动执行 'wsl --shutdown'", output)
        self.assertNotIn("✗ ghostty", output)
        self.assertNotIn("手动执行 'wsl --shutdown'", self.run_bootstrap().stdout)

    def test_headless_wsl_skips_zed(self):
        windows_home = self.windows()
        self.run_bootstrap()
        self.assertTrue((windows_home / ".wslconfig").is_file())
        self.assertFalse((self.home / ".config/zed").exists())
        self.assertFalse((self.home / ".config/Code").exists())

    def test_vscode_cursor_merge_preserves_other_settings_and_comments(self):
        self.graphical()
        target = self.home / ".config/Code/User/settings.json"
        target.parent.mkdir(parents=True)
        target.write_text('''{
    // Keep personal settings and their comments.
    "editor.fontSize": 18,
    "custom.url": "https://example.invalid/path/, }",
    "editor.cursorStyle": "line", // Replace only its value.
    "workbench.colorCustomizations": {
        "statusBar.background": "#123456",
        "editorCursor.foreground": "#FFFFFF",
    },
}
''')
        original = target.read_text()
        self.run_bootstrap()
        merged = target.read_text()
        self.assertIn('// Keep personal settings and their comments.', merged)
        self.assertIn('// Replace only its value.', merged)
        self.assertIn('"editor.fontSize": 18', merged)
        self.assertIn('"statusBar.background": "#123456"', merged)
        self.assertIn('"editor.cursorStyle": "block"', merged)
        self.assertIn('"editorCursor.foreground": "#FEDFE1"', merged)
        self.assertIn('"terminalCursor.foreground": "#FEDFE1"', merged)
        self.assertIn('https://example.invalid/path/, }', merged)
        self.assertEqual(self.saved(self.backups()[0], target).read_text(), original)
        before = self.snapshot()
        self.run_bootstrap()
        self.assertEqual(before, self.snapshot())
        self.repo.rename(self.base / "source unavailable")
        self.assertEqual(target.read_text(), merged)
        self.assertFalse(target.is_symlink())

    def test_invalid_vscode_settings_fail_before_any_changes(self):
        self.graphical()
        target = self.home / ".config/Code/User/settings.json"
        target.parent.mkdir(parents=True)
        target.write_text('{invalid settings')
        before = self.snapshot()
        self.run_bootstrap(success=False)
        self.assertEqual(before, self.snapshot())

    def test_missing_vscode_settings_are_created_with_cursor_preferences(self):
        self.graphical()
        self.run_bootstrap()
        settings = json.loads((self.home / ".config/Code/User/settings.json").read_text())
        expected = json.loads((self.repo / ".config/Code/User/settings.json").read_text())
        self.assertEqual(settings, expected)

    def test_missing_windows_home_is_reported(self):
        self.env["TEST_WSL"] = "1"
        self.command("cmd.exe", "printf '%s\\r\\n' 'C:\\Users\\Missing'\n")
        self.command("wslpath", 'printf "%s/nonexistent\\n" "$HOME"\n')
        output = self.run_bootstrap().stdout
        self.assertIn("未能定位 Windows 用户目录", output)
        self.assertFalse((self.home / "nonexistent").exists())

    def test_plugin_empty_directory_is_not_reported_as_installed(self):
        (self.home / ".oh-my-zsh/custom/plugins/zsh-autosuggestions").mkdir(parents=True)
        output = self.run_bootstrap().stdout
        self.assertIn("✗ 插件 zsh-autosuggestions", output)

    def test_optional_local_configuration_is_copied_and_loaded(self):
        (self.repo / ".zshrc.local").write_text("export DOTFILES_LOCAL_TEST=preserved\n")
        self.run_bootstrap()
        self.repo.rename(self.base / "source unavailable")
        self.assertFalse((self.home / ".zshrc.local").is_symlink())
        if shutil.which("zsh"):
            result = self.zsh('source "$HOME/.zshrc"; print "$DOTFILES_LOCAL_TEST"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("preserved", result.stdout)

    def test_existing_local_link_is_detached_without_an_override_source(self):
        source = self.base / "local source"
        source.write_text("export DOTFILES_LOCAL_TEST=preserved\n")
        target = self.home / ".zshrc.local"
        target.symlink_to(source)
        self.run_bootstrap()
        source.unlink()
        self.assertFalse(target.is_symlink())
        self.assertIn("preserved", target.read_text())

    def test_existing_regular_local_configuration_is_preserved(self):
        target = self.home / ".zshrc.local"
        target.write_text("export DOTFILES_LOCAL_TEST=preserved\n")
        self.run_bootstrap()
        self.assertEqual(target.read_text(), "export DOTFILES_LOCAL_TEST=preserved\n")

    def zsh(self, code):
        return subprocess.run(["/usr/bin/zsh", "-dfc", code], env=self.env,
                              capture_output=True, text=True)

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    def test_nvm_selected_version_is_not_overridden(self):
        for version in ("v20.0.0", "v22.0.0"):
            node = self.home / ".nvm/versions/node" / version / "bin/node"
            node.parent.mkdir(parents=True)
            node.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
            node.chmod(0o755)
        (self.home / ".nvm/nvm.sh").write_text(
            'export NVM_BIN="$NVM_DIR/versions/node/v20.0.0/bin"\n'
            'export PATH="$NVM_BIN:$PATH"\n')
        self.run_bootstrap()
        result = self.zsh('source "$HOME/.zshrc"; node --version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip().endswith("v20.0.0"), result.stdout)

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    def test_clipboard_aliases_follow_session(self):
        for command in ("wl-copy", "wl-paste", "xclip"):
            self.command(command, ":\n")
        self.run_bootstrap()
        for display, wayland, expected in (
            (":0", "wayland-0", "wl-copy"),
            (":0", "", "xclip -selection clipboard"),
            ("", "", "no-clipboard-alias"),
        ):
            with self.subTest(display=display, wayland=wayland):
                self.env.update(DISPLAY=display, WAYLAND_DISPLAY=wayland)
                result = self.zsh('source "$HOME/.zshrc"; alias cl-copy || print no-clipboard-alias')
                self.assertIn(expected, result.stdout)

    def test_zed_configuration_contains_no_copilot_registration(self):
        settings = json.loads((ROOT / ".config/zed/settings.json").read_text())
        self.assertNotIn("agent_servers", settings)
        self.assertEqual(settings["ui_font_size"], 24)
        self.assertEqual(settings["buffer_font_size"], 20)


if __name__ == "__main__":
    unittest.main()
