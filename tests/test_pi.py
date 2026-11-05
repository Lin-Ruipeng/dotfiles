"""Pi deployment integration tests: all installers and Pi commands are local fakes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_bootstrap as config_tests

ROOT = config_tests.ROOT


@unittest.skipUnless(shutil.which("node"), "Node is required to test the JSON helper")
class PiBootstrapTests(unittest.TestCase):
    command = config_tests.BootstrapTests.command
    backups = config_tests.BootstrapTests.backups
    saved = config_tests.BootstrapTests.saved
    snapshot = config_tests.BootstrapTests.snapshot
    graphical = config_tests.BootstrapTests.graphical
    windows = config_tests.BootstrapTests.windows

    def setUp(self):
        config_tests.BootstrapTests.setUp(self)
        for name in ("scripts/setup_pi.sh", "scripts/pi_settings.js", ".pi/agent/AGENTS.md"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.assets = self.base / "fixtures"
        self.assets.mkdir()
        self.agent = self.home / ".pi/agent"
        self.logfile = self.base / "commands.log"
        self.env.update(TEST_COMMAND_LOG=str(self.logfile), TEST_FIXTURES=str(self.assets),
                        TEST_REAL_NODE=shutil.which("node"), TEST_LTS="v26.1.2",
                        XDG_DATA_HOME=str(self.home / ".local/share"))
        self.env.pop("PI_SELF_UPDATE_COMMAND", None)
        self.env["PATH"] = f"{self.bin}:{self.home}/.local/bin:/usr/bin:/bin"
        (self.assets / "nvm.sh").write_text('''nvm() {
  printf 'nvm %s\\n' "$*" >> "$TEST_COMMAND_LOG"
  case "$1" in
    install)
      [ "${TEST_NODE_FAIL:-0}" = 0 ] || return 23
      mkdir -p "$NVM_DIR/versions/node/$TEST_LTS/bin"
      cp "$TEST_FIXTURES/node" "$NVM_DIR/versions/node/$TEST_LTS/bin/node"
      cp "$TEST_FIXTURES/npm" "$NVM_DIR/versions/node/$TEST_LTS/bin/npm"
      ;;
    use) export PATH="$NVM_DIR/versions/node/$TEST_LTS/bin:$PATH" ;;
    current) printf '%s\\n' "$TEST_LTS" ;;
    alias) mkdir -p "$NVM_DIR/alias"; printf '%s\\n' "$3" > "$NVM_DIR/alias/default" ;;
    *) return 24 ;;
  esac
}
''')
        (self.assets / "node").write_text('#!/bin/sh\nexec "$TEST_REAL_NODE" "$@"\n')
        (self.assets / "npm").write_text('#!/bin/sh\nprintf "npm %s\\n" "$*" >> "$TEST_COMMAND_LOG"\n')
        (self.assets / "pi").write_text('#!/bin/sh\nexec node "$TEST_FIXTURES/pi_mock.js" "$@"\n')
        for name in ("node", "npm", "pi"):
            (self.assets / name).chmod(0o755)
        (self.assets / "nvm-installer.sh").write_text('''[ "$PROFILE" = /dev/null ] || exit 70
mkdir -p "$NVM_DIR"
cp "$TEST_FIXTURES/nvm.sh" "$NVM_DIR/nvm.sh"
''')
        (self.assets / "pi-installer.sh").write_text('''# Refuse interactive execution: the real installer would ask questions.
if ( : </dev/tty ) 2>/dev/null; then exit 71; fi
[ ! -t 1 ] || exit 72
[ "${TEST_INSTALL_FAIL:-0}" = 0 ] || exit 25
agent=${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}
mkdir -p "$agent/bin" "$agent/install" "$HOME/.local/bin"
cp "$TEST_FIXTURES/pi" "$agent/bin/pi"
printf '{"kind":"pi-managed-install","layout":"releases-v1"}\\n' > "$agent/install/managed-install.json"
ln -sf "$agent/bin/pi" "$HOME/.local/bin/pi"
''')
        (self.assets / "pi_mock.js").write_text('''const fs = require('node:fs');
const path = require('node:path');
const args = process.argv.slice(2);
fs.appendFileSync(process.env.TEST_COMMAND_LOG, 'pi ' + args.join(' ') + '\\n');
const agent = process.env.PI_CODING_AGENT_DIR;
if (args[0] === 'update') process.exit(Number(process.env.TEST_HOST_FAIL || 0));
if (args[0] === 'install') {
  if (!args.includes('--no-approve')) process.exit(80);
  if (args[1] === process.env.TEST_PLUGIN_FAIL) process.exit(26);
  const name = args[1].slice(4);
  const folder = path.join(agent, 'npm/node_modules', name);
  fs.mkdirSync(folder, {recursive:true});
  fs.writeFileSync(path.join(folder, 'package.json'), JSON.stringify({name,version:'9.9.9'}));
  process.exit(0);
}
if (args[0] === 'mcp' && args[1] === 'add') {
  const target = path.join(agent, 'mcp.json');
  if (process.env.TEST_MCP_FAIL) {
    fs.writeFileSync(target, 'partial output');
    process.exit(27);
  }
  const value = fs.existsSync(target) ? JSON.parse(fs.readFileSync(target,'utf8')) : {};
  value.mcpServers ??= {};
  value.mcpServers.context7 = {url:args[args.indexOf('--url')+1],exposure:args[args.indexOf('--exposure')+1]};
  fs.writeFileSync(target, JSON.stringify(value,null,2)+'\\n');
  process.exit(0);
}
process.exit(81);
''')
        self.command("curl", '''printf 'curl %s\\n' "$*" >> "$TEST_COMMAND_LOG"
case "$*" in
  *nvm-sh/nvm*)
    [ "${TEST_CURL_FAIL:-0}" = 0 ] || { printf 'exit 0\\n'; exit 22; }
    cat "$TEST_FIXTURES/nvm-installer.sh" ;;
  *pi.dev/install.sh*)
    [ "${TEST_PI_CURL_FAIL:-0}" = 0 ] || { printf 'exit 0\\n'; exit 29; }
    cat "$TEST_FIXTURES/pi-installer.sh" ;;
  *) exit 82 ;;
esac
''')

    def run_bootstrap(self, *args, success=True):
        result = subprocess.run(["bash", str(self.repo / "bootstrap.sh"), *args],
                                env=self.env, capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def commands(self):
        return self.logfile.read_text() if self.logfile.exists() else ""

    def assert_plugin_installs(self, planner):
        packages = (
            "@juicesharp/rpiv-ask-user-question", "pi-subagents", "pi-web-access", "pi-extmgr", planner,
        )
        commands = [line for line in self.commands().splitlines() if line.startswith("pi install ")]
        self.assertCountEqual(commands, [f"pi install npm:{package} --no-approve" for package in packages])

    def settings(self):
        return json.loads((self.agent / "settings.json").read_text())

    def write_json(self, target, data):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))

    def existing_nvm(self):
        folder = self.home / ".nvm"
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.assets / "nvm.sh", folder / "nvm.sh")

    def existing_pi(self):
        (self.agent / "bin").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.assets / "pi", self.agent / "bin/pi")
        (self.agent / "bin/pi").chmod(0o755)
        self.write_json(self.agent / "install/managed-install.json",
                        {"kind": "pi-managed-install", "layout": "releases-v1"})
        (self.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        (self.home / ".local/bin/pi").symlink_to(self.agent / "bin/pi")

    def test_fresh_headless_installs_only_terminal_suite(self):
        output = self.run_bootstrap().stdout
        self.assertIn("已帮你安装 NVM", output)
        commands = self.commands()
        self.assertIn("nvm install --lts", commands)
        self.assertIn("nvm alias default v26.1.2", commands)
        self.assertEqual((self.home / ".nvm/alias/default").read_text().strip(), "v26.1.2")
        self.assertIn("https://pi.dev/install.sh", commands)
        self.assert_plugin_installs("pi-plan")
        self.assertNotIn("pi mcp", commands)
        self.assertFalse((self.agent / "mcp.json").exists())
        self.assertEqual(len(self.settings()["packages"]), 5)
        self.assertIn("不自动恢复", output)
        self.repo.rename(self.base / "source removed")
        self.assertNotIn(str(self.repo), (self.agent / "settings.json").read_text())
        instructions = self.agent / "AGENTS.md"
        self.assertFalse(instructions.is_symlink())
        self.assertEqual(instructions.read_bytes(), (ROOT / ".pi/agent/AGENTS.md").read_bytes())
        self.assertTrue((self.agent / "bin/pi").is_file())

    def test_existing_installs_update_and_gui_registers_manual_login(self):
        self.existing_nvm()
        self.existing_pi()
        self.graphical()
        output = self.run_bootstrap().stdout
        self.assertNotIn("已帮你安装 NVM", output)
        self.assertNotIn("curl ", self.commands())
        self.assertIn("pi update --no-approve", self.commands())
        self.assert_plugin_installs("@plannotator/pi-extension")
        self.assertIn("pi mcp add context7 --url https://mcp.context7.com/mcp --exposure direct", self.commands())
        self.assertNotIn("pi mcp login", self.commands())
        self.assertIn("用户手动完成：pi mcp login context7", output)
        self.assertEqual(json.loads((self.agent / "mcp.json").read_text())["mcpServers"]["context7"],
                         {"url": "https://mcp.context7.com/mcp", "exposure": "direct"})

    def test_skip_pi_and_dry_run_never_execute_installers_or_cli(self):
        for flags in (("--skip-pi",), ("--dry-run",), ("--dry-run", "--skip-pi")):
            with self.subTest(flags=flags):
                self.graphical()
                before = self.snapshot()
                self.run_bootstrap(*flags)
                self.assertEqual(self.commands(), "")
                self.assertFalse((self.home / ".nvm").exists())
                self.assertFalse(self.agent.exists())
                if "--dry-run" in flags:
                    self.assertEqual(before, self.snapshot())

    def test_dry_run_with_old_links_changes_nothing(self):
        self.existing_nvm()
        self.existing_pi()
        source = self.repo / "pi-local.json"
        source.write_text('{"packages":[]}')
        (self.agent / "settings.json").symlink_to(source)
        before = self.snapshot()
        original = source.read_bytes()
        self.run_bootstrap("--dry-run")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(self.commands(), "")

    def test_planner_switch_disables_all_resources_preserves_customizations(self):
        extra = {"source": "npm:user-extra@1.0.0", "extensions": ["custom.ts"]}
        original = {"model": "personal", "packages": [
            extra, {"source": "npm:@plannotator/pi-extension@0.1.0", "skills": ["custom"]},
            {"source": "npm:pi-plan@0.1.0", "extensions": [], "autoload": False},
            "npm:pi-web-access@0.1.0"]}
        self.write_json(self.agent / "settings.json", original)
        self.run_bootstrap()
        settings = self.settings()
        self.assertEqual(settings["model"], "personal")
        self.assertIn(extra, settings["packages"])
        self.assertIn("npm:pi-plan", settings["packages"])
        disabled = next(p for p in settings["packages"] if isinstance(p, dict) and "plannotator" in p["source"])
        self.assertEqual(disabled, {"source": "npm:@plannotator/pi-extension",
                                   "extensions": [], "skills": [], "prompts": [], "themes": []})
        self.assertIn("npm:pi-web-access", settings["packages"])
        backup = next(self.saved(b, self.agent / "settings.json") for b in self.backups()
                      if self.saved(b, self.agent / "settings.json").exists())
        self.assertEqual(json.loads(backup.read_text()), original)
        self.assertNotIn("pi install npm:user-extra", self.commands())
        self.graphical()
        self.run_bootstrap()
        entries = self.settings()["packages"]
        self.assertIn("npm:@plannotator/pi-extension", entries)
        self.assertIn({"source": "npm:pi-plan", "extensions": [], "skills": [], "prompts": [], "themes": []}, entries)

    def test_context7_backup_preserves_other_servers_and_credentials(self):
        self.graphical()
        original = {"other": True, "mcpServers": {"custom": {"command": "tool"},
                    "context7": {"url": "https://old.invalid", "headers": {"example": "private"}}}}
        self.write_json(self.agent / "mcp.json", original)
        self.write_json(self.agent / "mcp-auth.json", {"test": "keep"})
        self.run_bootstrap()
        after = json.loads((self.agent / "mcp.json").read_text())
        self.assertEqual(after["mcpServers"]["custom"], original["mcpServers"]["custom"])
        self.assertTrue(after["other"])
        self.assertEqual(json.loads((self.agent / "mcp-auth.json").read_text()), {"test": "keep"})
        backup = next(self.saved(b, self.agent / "mcp.json") for b in self.backups()
                      if self.saved(b, self.agent / "mcp.json").exists())
        self.assertEqual(json.loads(backup.read_text()), original)
        before = (self.agent / "mcp.json").stat().st_mtime_ns
        self.run_bootstrap()
        self.assertEqual(self.commands().count("pi mcp add context7"), 1)
        self.assertEqual((self.agent / "mcp.json").stat().st_mtime_ns, before)

    def test_headless_does_not_touch_existing_mcp(self):
        target = self.agent / "mcp.json"
        target.parent.mkdir(parents=True)
        target.write_text("even invalid local MCP config is preserved")
        self.run_bootstrap()
        self.assertEqual(target.read_text(), "even invalid local MCP config is preserved")
        self.assertNotIn("pi mcp", self.commands())

    def test_wslg_selects_gui_suite(self):
        self.graphical()
        self.windows()
        self.run_bootstrap()
        self.assertIn("npm:@plannotator/pi-extension", self.commands())
        self.assertIn("pi mcp add", self.commands())
        self.assertFalse((self.home / ".config/ghostty").exists())

    def test_plugin_failure_continues_others_and_context7(self):
        self.graphical()
        self.env["TEST_PLUGIN_FAIL"] = "npm:pi-subagents"
        output = self.run_bootstrap(success=False).stdout
        self.assertIn("pi install npm:pi-extmgr", self.commands())
        self.assertIn("pi mcp add", self.commands())
        self.assertIn("✗ 插件 pi-subagents", output)
        self.assertIn("✓ 插件 pi-web-access", output)
        self.assertIn("== 依赖检查 ==", output)
        self.assertIn("存在失败", output)

    def test_prerequisite_failures_skip_dependent_steps(self):
        self.env["TEST_NODE_FAIL"] = "1"
        output = self.run_bootstrap(success=False).stdout
        self.assertNotIn("pi.dev/install.sh", self.commands())
        self.assertNotIn("pi install", self.commands())
        self.assertIn("NVM 最新 LTS", output)
        self.assertTrue((self.home / ".zshrc").is_file())

    def test_download_pipeline_failure_is_reported(self):
        self.env["TEST_CURL_FAIL"] = "1"
        output = self.run_bootstrap(success=False).stdout
        self.assertNotIn("nvm install", self.commands())
        self.assertNotIn("已帮你安装 NVM", output)
        self.assertIn("退出码 22", output)

    def test_pi_download_failure_is_reported(self):
        self.env["TEST_PI_CURL_FAIL"] = "1"
        output = self.run_bootstrap(success=False).stdout
        self.assertIn("退出码 29", output)
        self.assertNotIn("pi install", self.commands())

    def test_host_install_and_update_failures_skip_extensions(self):
        self.env["TEST_INSTALL_FAIL"] = "1"
        self.run_bootstrap(success=False)
        self.assertNotIn("pi install", self.commands())
        self.env.pop("TEST_INSTALL_FAIL")
        self.existing_pi()
        self.env["TEST_HOST_FAIL"] = "28"
        self.run_bootstrap(success=False)
        self.assertNotIn("pi install", self.commands())

    def test_failed_mcp_registration_keeps_original_and_cleans_stage(self):
        self.graphical()
        original = {"mcpServers": {"custom": {"command": "tool"}}}
        self.write_json(self.agent / "mcp.json", original)
        self.env["TEST_MCP_FAIL"] = "1"
        output = self.run_bootstrap(success=False).stdout
        self.assertEqual(json.loads((self.agent / "mcp.json").read_text()), original)
        self.assertEqual(list(self.agent.glob(".dotfiles-*")), [])
        self.assertIn("Context7 注册（原配置保留）", output)

    def test_settings_and_directory_links_become_independent(self):
        source = self.repo / "old pi"
        source.mkdir()
        original = {"model": "local", "packages": []}
        self.write_json(source / "settings.json", original)
        (source / "extra").write_text("preserve")
        (self.home / ".pi").mkdir()
        self.agent.symlink_to(source, target_is_directory=True)
        self.run_bootstrap()
        self.assertFalse(self.agent.is_symlink())
        self.assertEqual((self.agent / "extra").read_text(), "preserve")
        self.assertEqual(json.loads((source / "settings.json").read_text()), original)
        self.repo.rename(self.base / "source unavailable")
        self.assertTrue((self.agent / "settings.json").read_text())
        for backup in self.backups():
            for target in backup.rglob("settings.json"):
                self.assertFalse(target.is_symlink())
                json.loads(target.read_text())

    def test_backup_failure_preserves_original_and_skips_pi(self):
        self.existing_nvm()
        original = {"packages": [], "model": "keep"}
        self.write_json(self.agent / "settings.json", original)
        self.command("cp", '''case "$*" in *'.dotfiles-backup'*settings.json*) exit 42 ;; esac
exec /bin/cp "$@"
''')
        self.run_bootstrap(success=False)
        self.assertEqual(self.settings(), original)
        self.assertNotIn("pi.dev/install.sh", self.commands())
        self.assertNotIn("pi install", self.commands())

    def test_invalid_settings_fail_without_replacing_file(self):
        self.agent.mkdir(parents=True)
        (self.agent / "settings.json").write_text('{broken secret data')
        result = self.run_bootstrap(success=False)
        self.assertEqual((self.agent / "settings.json").read_text(), '{broken secret data')
        self.assertNotIn("broken secret data", result.stderr)
        self.assertNotIn("pi.dev/install.sh", self.commands())

    def test_private_node_entry_is_retired_with_independent_backup(self):
        versions = self.home / ".local/share/pi-node/releases/old"
        (versions / "bin").mkdir(parents=True)
        (versions / "bin/node").write_text("old runtime")
        current = versions.parent.parent / "current"
        current.symlink_to(versions, target_is_directory=True)
        self.run_bootstrap()
        self.assertFalse(current.exists())
        self.assertFalse(current.is_symlink())
        self.assertEqual((versions / "bin/node").read_text(), "old runtime")
        backup = next(self.saved(b, current, "directories") for b in self.backups()
                      if self.saved(b, current, "directories").exists())
        versions.rename(versions.with_name("unavailable"))
        self.assertEqual((backup / "bin/node").read_text(), "old runtime")
        self.assertFalse(backup.is_symlink())

    def test_private_node_move_failure_keeps_entry(self):
        current = self.home / ".local/share/pi-node/current"
        (current / "bin").mkdir(parents=True)
        (current / "bin/node").write_text("old runtime")
        self.command("mv", '''case "$*" in *retired*current*) exit 43 ;; esac
exec /bin/mv "$@"
''')
        self.run_bootstrap(success=False)
        self.assertEqual((current / "bin/node").read_text(), "old runtime")
        self.assertNotIn("pi install", self.commands())

    def test_private_node_plain_directory_and_dangling_link(self):
        current = self.home / ".local/share/pi-node/current"
        (current / "bin").mkdir(parents=True)
        (current / "bin/node").write_text("old runtime")
        self.run_bootstrap()
        self.assertFalse(current.exists())
        self.assertTrue(any((self.saved(b, current, "directories") / "bin/node").is_file()
                            for b in self.backups()))
        current.symlink_to("missing runtime")
        self.run_bootstrap()
        self.assertFalse(current.is_symlink())
        self.assertTrue(any((b / "links" / f"directories{current}.target").is_file()
                            for b in self.backups()))

    def test_default_alias_link_is_detached_before_nvm_writes(self):
        self.existing_nvm()
        alias = self.home / ".nvm/alias/default"
        alias.parent.mkdir()
        source = self.repo / "old-default"
        source.write_text("v20.0.0\n")
        alias.symlink_to(source)
        self.run_bootstrap()
        self.assertFalse(alias.is_symlink())
        self.assertEqual(alias.read_text(), "v26.1.2\n")
        self.assertEqual(source.read_text(), "v20.0.0\n")
        backup = next(self.saved(b, alias) for b in self.backups() if self.saved(b, alias).is_file())
        self.repo.rename(self.base / "source gone")
        self.assertEqual(backup.read_text(), "v20.0.0\n")

    def test_settings_file_link_is_detached_before_cli(self):
        self.agent.mkdir(parents=True)
        source = self.repo / "old-settings.json"
        original = {"model": "keep", "packages": []}
        source.write_text(json.dumps(original))
        target = self.agent / "settings.json"
        target.symlink_to(source)
        self.run_bootstrap()
        self.assertFalse(target.is_symlink())
        self.assertEqual(json.loads(source.read_text()), original)
        backup = next(self.saved(b, target) for b in self.backups() if self.saved(b, target).is_file())
        self.repo.rename(self.base / "gone")
        self.assertEqual(json.loads(backup.read_text()), original)

    def test_non_managed_pi_is_not_uninstalled_or_replaced(self):
        self.command("pi", "exit 83\n")
        original = (self.bin / "pi").read_bytes()
        result = self.run_bootstrap(success=False)
        output = result.stdout + result.stderr
        self.assertEqual((self.bin / "pi").read_bytes(), original)
        self.assertNotIn("pi.dev/install.sh", self.commands())
        self.assertNotIn("npm uninstall", self.commands())
        self.assertIn("手动使用官网 curl 迁移", output)

    def test_custom_agent_directory_is_used(self):
        self.agent = self.home / "custom pi agent"
        self.env["PI_CODING_AGENT_DIR"] = str(self.agent)
        self.run_bootstrap()
        self.assertTrue((self.agent / "settings.json").is_file())
        self.assertTrue((self.agent / "bin/pi").is_file())
        self.assertEqual((self.agent / "AGENTS.md").read_bytes(), (ROOT / ".pi/agent/AGENTS.md").read_bytes())
        self.assertFalse((self.home / ".pi").exists())

    def test_agent_directory_inside_repository_is_rejected(self):
        self.env["PI_CODING_AGENT_DIR"] = str(self.repo / "pi")
        self.run_bootstrap(success=False)
        self.assertFalse((self.repo / "pi").exists())
        self.assertNotIn("pi.dev/install.sh", self.commands())

    def test_repository_resource_reference_is_rejected(self):
        self.agent.mkdir(parents=True)
        resource = self.repo / "extension.ts"
        resource.write_text("// local resource")
        link = self.agent / "extension.ts"
        link.symlink_to(resource)
        original = {"extensions": ["./extension.ts"], "packages": []}
        self.write_json(self.agent / "settings.json", original)
        result = self.run_bootstrap(success=False)
        self.assertIn("仍引用本仓库", result.stderr)
        self.assertEqual(self.settings(), original)
        self.assertNotIn("pi.dev/install.sh", self.commands())

    def test_pi_instructions_backup_and_idempotency(self):
        instructions = self.agent / "AGENTS.md"
        instructions.parent.mkdir(parents=True)
        instructions.write_text("# Previous user instructions\n")
        self.run_bootstrap()
        self.assertEqual(instructions.read_bytes(), (ROOT / ".pi/agent/AGENTS.md").read_bytes())
        backup = next(self.saved(b, instructions) for b in self.backups()
                      if self.saved(b, instructions).is_file())
        self.assertEqual(backup.read_text(), "# Previous user instructions\n")
        before = instructions.stat().st_mtime_ns
        self.run_bootstrap()
        self.assertEqual(instructions.stat().st_mtime_ns, before)

    def test_pi_instructions_link_becomes_independent(self):
        self.agent.mkdir(parents=True)
        source = self.repo / "old-instructions.md"
        source.write_text("# Old linked instructions\n")
        instructions = self.agent / "AGENTS.md"
        instructions.symlink_to(source)
        self.run_bootstrap()
        self.assertFalse(instructions.is_symlink())
        self.assertEqual(source.read_text(), "# Old linked instructions\n")
        backup = next(self.saved(b, instructions) for b in self.backups()
                      if self.saved(b, instructions).is_file())
        self.repo.rename(self.base / "source unavailable")
        self.assertEqual(instructions.read_bytes(), (ROOT / ".pi/agent/AGENTS.md").read_bytes())
        self.assertEqual(backup.read_text(), "# Old linked instructions\n")

    def test_missing_pi_instructions_fail_before_any_changes(self):
        (self.repo / ".pi/agent/AGENTS.md").unlink()
        before = self.snapshot()
        self.run_bootstrap(success=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.commands(), "")

    def test_retired_todo_is_not_loaded_or_installed(self):
        cache = self.agent / "npm/node_modules/@juicesharp/rpiv-todo/package.json"
        self.write_json(cache, {"name": "@juicesharp/rpiv-todo", "version": "2.15.0"})
        original = {"packages": ["npm:@juicesharp/rpiv-todo",
                    {"source": "npm:@juicesharp/rpiv-todo@2.15.0", "extensions": ["index.ts"]},
                    "npm:user-extra"], "model": "personal"}
        self.write_json(self.agent / "settings.json", original)
        self.run_bootstrap()
        self.assertNotIn("rpiv-todo", json.dumps(self.settings()))
        self.assertIn("npm:user-extra", self.settings()["packages"])
        self.assertEqual(self.settings()["model"], "personal")
        self.assertNotIn("npm:@juicesharp/rpiv-todo", self.commands())
        self.assertTrue(cache.is_file())
        backup = next(self.saved(b, self.agent / "settings.json") for b in self.backups()
                      if self.saved(b, self.agent / "settings.json").is_file())
        self.assertEqual(json.loads(backup.read_text()), original)


if __name__ == "__main__":
    unittest.main()
