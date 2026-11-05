#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/bootstrap.sh"
BACKUP_DIR="${DOTFILES_PI_BACKUP_DIR:-}"
PI_PHASE="预检"
PI_FAILURES=()
PI_SUCCESSES=()
PI_SKIPPED=()
PI_MODE=headless
PI_PLANNER=pi-plan
PI_HELPER="$REPO_DIR/scripts/pi_settings.js"
PI_SOURCE_STAGE=""

pi_finish() {
  local status="$1" item
  if [ "$DRY_RUN" -eq 0 ]; then
    if [ "$status" -ne 0 ] && [ "$PI_PHASE" != done ]; then
      PI_FAILURES+=("$PI_PHASE（退出码 $status）")
      PI_SKIPPED+=("依赖失败前置步骤的后续 Pi 操作")
    fi
    log "== Pi 部署汇总 =="
    for item in "${PI_SUCCESSES[@]}"; do log "✓ $item"; done
    for item in "${PI_SKIPPED[@]}"; do log "⏭  $item"; done
    for item in "${PI_FAILURES[@]}"; do log "✗ $item"; done
    [ -z "$BACKUP_DIR" ] || log "本次备份目录: $BACKUP_DIR"
    if [ "$status" -ne 0 ]; then
      log "修复上述错误后重跑 bash bootstrap.sh；网络受限时先开启代理。"
    fi
  fi
  if [ -n "$PI_SOURCE_STAGE" ]; then rm -rf -- "$PI_SOURCE_STAGE"; fi
  cleanup
}

# Pi writes settings in place. Detach links and save the original before invoking it.
pi_protect_file() {
  local target="$1"
  ensure_directory "$(dirname "$target")"
  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -f "$target" ]; then
      copy_config "$target" "$target"
    elif [ -L "$target" ] && [ ! -e "$target" ]; then
      backup_target "$target" "files${target}"
      ACTIVE_STAGE="$(mktemp "$(dirname "$target")/.dotfiles-file.XXXXXX")"
      printf '{}\n' > "$ACTIVE_STAGE"
      mv -T -- "$ACTIVE_STAGE" "$target"
      ACTIVE_STAGE=""
    else
      die "Pi 配置不是普通文件: $target"
    fi
    backup_target "$target" "files${target}"
  fi
}

pi_prepare_nvm() {
  PI_PHASE="NVM 安装与加载"
  export NVM_DIR="$HOME/.nvm"
  local nvm_existing=0 name
  if [ -e "$NVM_DIR" ] || [ -L "$NVM_DIR" ]; then nvm_existing=1; fi
  ensure_directory "$NVM_DIR"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    # Keep the pre-install contents, including incomplete installations.
    if [ "$nvm_existing" -eq 1 ]; then backup_target "$NVM_DIR" "directories${NVM_DIR}"; fi
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh |
      PROFILE=/dev/null NODE_VERSION= NVM_DIR="$NVM_DIR" bash
    [ -s "$NVM_DIR/nvm.sh" ] || die "NVM 安装后未找到 nvm.sh"
    log "已帮你安装 NVM：$NVM_DIR"
  fi
  for name in nvm.sh nvm-exec bash_completion; do
    if [ -L "$NVM_DIR/$name" ]; then pi_protect_file "$NVM_DIR/$name"; fi
  done
  # NVM supports shells without nounset; load without selecting an old default.
  set +u
  source "$NVM_DIR/nvm.sh" --no-use
  PI_PHASE="NVM 最新 LTS Node.js"
  pi_protect_file "$NVM_DIR/alias/default"
  nvm install --lts
  nvm use --lts
  local version
  version="$(nvm current)"
  [[ "$version" = v[0-9]* ]] || die "NVM 未选择有效 Node 版本"
  nvm alias default "$version"
  set -u
  NODE_BIN="$NVM_DIR/versions/node/$version/bin"
  [ "$(command -v node)" = "$NODE_BIN/node" ] || die "node 未使用 NVM 选中的版本"
  [ "$(command -v npm)" = "$NODE_BIN/npm" ] || die "npm 未使用 NVM 选中的版本"
  PI_SUCCESSES+=("NVM / Node $version（最新 LTS，已设为默认）")
}

pi_prepare_state() {
  PI_PHASE="Pi 配置预检与独立备份"
  PI_AGENT_DIR="$(node "$PI_HELPER" resolve "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" "$PWD" "$HOME")"
  case "$PI_AGENT_DIR" in "$REPO_DIR"|"$REPO_DIR"/*) die "Pi 安装目录不能位于仓库内" ;; esac
  export PI_CODING_AGENT_DIR="$PI_AGENT_DIR"
  PI_BIN="$PI_AGENT_DIR/bin/pi"
  validate_config "$REPO_DIR/.pi/agent/AGENTS.md" "$PI_AGENT_DIR/AGENTS.md"
  node "$PI_HELPER" settings-check "$PI_AGENT_DIR/settings.json" "$PI_MODE" "$REPO_DIR" >/dev/null
  if [ "$PI_MODE" = gui ]; then
    node "$PI_HELPER" mcp-check "$PI_AGENT_DIR/mcp.json" "$REPO_DIR" >/dev/null
  fi
  if [ -n "$PI_PREVIOUS_BIN" ]; then
    [ "$(readlink -f -- "$PI_PREVIOUS_BIN")" = "$(readlink -f -- "$PI_BIN")" ] ||
      die "发现其他来源的 Pi：$PI_PREVIOUS_BIN；请先手动使用官网 curl 迁移，或使用 --skip-pi"
  fi
  if [ -e "$PI_BIN" ] || [ -L "$PI_BIN" ]; then
    node "$PI_HELPER" managed "$PI_AGENT_DIR"
  fi
  ensure_directory "$PI_AGENT_DIR"
  ensure_directory "$PI_AGENT_DIR/bin"
  ensure_directory "$PI_AGENT_DIR/install"
  ensure_directory "$PI_AGENT_DIR/npm"
  ensure_directory "$PI_AGENT_DIR/npm/node_modules"
  if [ -L "$PI_BIN" ]; then pi_protect_file "$PI_BIN"; fi
  pi_protect_file "$PI_AGENT_DIR/settings.json"
  # Other state can also be rewritten by Pi; detach existing file links first.
  local name
  for name in auth.json mcp-auth.json trust.json models-store.json; do
    if [ -L "$PI_AGENT_DIR/$name" ]; then pi_protect_file "$PI_AGENT_DIR/$name"; fi
  done
  if [ "$PI_MODE" = gui ]; then pi_protect_file "$PI_AGENT_DIR/mcp.json"; fi
  copy_config "$REPO_DIR/.pi/agent/AGENTS.md" "$PI_AGENT_DIR/AGENTS.md"
  PI_SUCCESSES+=("Pi 用户级指令 AGENTS.md 已部署")
  local private_node="${XDG_DATA_HOME:-$HOME/.local/share}/pi-node/current"
  if [ -e "$private_node" ] || [ -L "$private_node" ]; then
    ensure_directory "$(dirname "$private_node")"
    backup_target "$private_node" "directories${private_node}"
    mkdir -p -- "$BACKUP_DIR/retired$(dirname "$private_node")"
    mv -T -- "$private_node" "$BACKUP_DIR/retired$private_node"
    log "✓ 已备份并停用 Pi 私有 Node 入口，保留真实版本目录；Pi 将使用 NVM Node"
  fi
}

pi_merge_settings() {
  local target="$PI_AGENT_DIR/settings.json" state
  state="$(node "$PI_HELPER" settings-check "$target" "$PI_MODE" "$REPO_DIR")"
  if [ "$state" = changed ]; then
    PI_SOURCE_STAGE="$(mktemp "$PI_AGENT_DIR/.dotfiles-settings.XXXXXX")"
    node "$PI_HELPER" settings-merge "$target" "$PI_MODE" "$REPO_DIR" > "$PI_SOURCE_STAGE"
    copy_config "$PI_SOURCE_STAGE" "$target"
    rm -- "$PI_SOURCE_STAGE"
    PI_SOURCE_STAGE=""
  fi
}

pi_install_host() {
  PI_PHASE="Pi 本体安装或更新"
  export PATH="$NODE_BIN:$HOME/.local/bin:$PATH"
  if [ -x "$PI_BIN" ]; then
    "$PI_BIN" update --no-approve
  else
    command -v setsid >/dev/null || die "Pi 自动安装需要 setsid（Ubuntu util-linux）；请手动准备后重试"
    # No controlling TTY and non-TTY stdout: never launch Pi or edit a profile.
    # --wait and both pipefail settings retain download/installer exit status.
    setsid --wait bash -o pipefail -c 'curl -fsSL https://pi.dev/install.sh | sh' </dev/null | cat
    [ -x "$PI_BIN" ] || die "官网安装后未找到 $PI_BIN"
    node "$PI_HELPER" managed "$PI_AGENT_DIR"
  fi
  PI_SUCCESSES+=("Pi 本体已同步最新版")
}

pi_install_extensions() {
  PI_PHASE="Pi 插件"
  local package
  for package in '@juicesharp/rpiv-ask-user-question' \
    pi-subagents pi-web-access pi-extmgr "$PI_PLANNER"; do
    if "$PI_BIN" install "npm:$package" --no-approve; then
      PI_SUCCESSES+=("插件 $package")
    else
      PI_FAILURES+=("插件 $package（可单独重试 pi install npm:$package --no-approve）")
    fi
  done
}

pi_setup_context7() {
  PI_PHASE="Context7 注册"
  if [ "$PI_MODE" != gui ]; then
    PI_SKIPPED+=("无 GUI：跳过 Context7，保留已有 MCP 配置")
    return
  fi
  local state
  state="$(node "$PI_HELPER" mcp-check "$PI_AGENT_DIR/mcp.json" "$REPO_DIR")"
  if [ "$state" = changed ]; then
    # Run the requested CLI against a disposable config, then atomically deploy it.
    PI_SOURCE_STAGE="$(mktemp -d "$PI_AGENT_DIR/.dotfiles-mcp.XXXXXX")"
    if [ -f "$PI_AGENT_DIR/mcp.json" ]; then
      cp -pL -- "$PI_AGENT_DIR/mcp.json" "$PI_SOURCE_STAGE/mcp.json"
    fi
    if PI_CODING_AGENT_DIR="$PI_SOURCE_STAGE" "$PI_BIN" mcp add context7 \
      --url https://mcp.context7.com/mcp --exposure direct --no-approve; then
      [ "$(node "$PI_HELPER" mcp-check "$PI_SOURCE_STAGE/mcp.json")" = unchanged ] || die "Context7 注册结果不符合要求"
      copy_config "$PI_SOURCE_STAGE/mcp.json" "$PI_AGENT_DIR/mcp.json"
      rm -rf -- "$PI_SOURCE_STAGE"
      PI_SOURCE_STAGE=""
    else
      PI_FAILURES+=("Context7 注册（原配置保留）")
      rm -rf -- "$PI_SOURCE_STAGE"
      PI_SOURCE_STAGE=""
      return
    fi
  fi
  PI_SUCCESSES+=("Context7 已注册（direct）")
  log "Context7 登录由用户手动完成：pi mcp login context7"
}

setup_pi() {
  if [ "${1:-}" = --dry-run ]; then DRY_RUN=1; fi
  trap 'pi_finish "$?"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  if has_gui; then PI_MODE=gui; PI_PLANNER='@plannotator/pi-extension'; fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log "[dry-run] 将按需安装 NVM（官方 v0.40.8，PROFILE=/dev/null）"
    log "[dry-run] 将通过 NVM 安装最新 LTS Node，并把具体版本设为 default"
    log "[dry-run] 将预检、备份并合并 Pi 配置，停用已有 Pi 私有 Node 入口"
    log "[dry-run] 将备份并复制 .pi/agent/AGENTS.md 到 \${PI_CODING_AGENT_DIR:-\$HOME/.pi/agent}/AGENTS.md，保存为独立文件"
    log "[dry-run] 首装：curl -fsSL https://pi.dev/install.sh | sh；已有官方 Pi：pi update"
    log "[dry-run] 将安装或更新问答、pi-subagents、pi-web-access、pi-extmgr 和 $PI_PLANNER"
    log "[dry-run] 将禁用已存在的另一计划插件的全部资源"
    if has_gui; then
      log "[dry-run] 将按需注册 Context7：https://mcp.context7.com/mcp（direct）；用户手动执行 pi mcp login context7"
    else
      log "[dry-run] 无 GUI：保留已有 MCP 配置"
    fi
    return
  fi
  command -v curl >/dev/null || die "缺少 curl，请手动安装：sudo apt install curl"
  PI_PREVIOUS_BIN="$(command -v pi || true)"
  pi_prepare_nvm
  pi_prepare_state
  pi_merge_settings
  pi_install_host
  pi_install_extensions
  pi_setup_context7
  if [ "$PI_MODE" = headless ]; then
    log "pi-plan 原版限制：规划时收缩工具列表，退出后不自动恢复其他插件工具；详见 README。"
  fi
  PI_PHASE=done
  [ "${#PI_FAILURES[@]}" -eq 0 ]
}

setup_pi "$@"
