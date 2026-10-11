#!/usr/bin/env bash
# 只复制配置，不安装软件。部署结果及新备份均独立于仓库。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
BACKUP_ROOT="$HOME/.dotfiles-backup"
BACKUP_DIR=""
DRY_RUN=0
SKIP_ZED=0
MISSING=0
ACTIVE_STAGE=""
ACTIVE_OLD_LINK=""
ACTIVE_DEST=""

log() { printf '%s\n' "$*"; }
die() { log "错误: $*" >&2; exit 1; }
is_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }
has_gui() { [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; }

usage() {
  log "用法: bash bootstrap.sh [--dry-run] [--skip-zed]"
  log "  --dry-run    仅预览，不修改任何文件"
  log "  --skip-zed   保留本机 Zed 设置，跳过 Zed 部署与依赖检查"
}

# 仅清理本次 mktemp 生成的临时副本；目录链接替换失败时恢复原链接。
cleanup() {
  if [ -n "$ACTIVE_OLD_LINK" ] && [ -L "$ACTIVE_OLD_LINK" ]; then
    if [ ! -e "$ACTIVE_DEST" ] && [ ! -L "$ACTIVE_DEST" ]; then
      mv -T -- "$ACTIVE_OLD_LINK" "$ACTIVE_DEST" || log "恢复失败，原链接保留于: $ACTIVE_OLD_LINK" >&2
    fi
  elif [ -n "$ACTIVE_OLD_LINK" ] && [ -f "$ACTIVE_OLD_LINK" ]; then
    rm -- "$ACTIVE_OLD_LINK"
  fi
  if [ -n "$ACTIVE_STAGE" ]; then
    rm -rf -- "$ACTIVE_STAGE"
  fi
}

ensure_backup_dir() {
  if [ -z "$BACKUP_DIR" ]; then
    mkdir -p -- "$BACKUP_ROOT"
    BACKUP_DIR="$(mktemp -d "$BACKUP_ROOT/$(date +%Y%m%d-%H%M%S).XXXXXX")"
    log "  备份目录: $BACKUP_DIR"
  fi
}

# 文件与目录分开保存，键包含完整目标路径，避免重名和父子备份覆盖。
# 可读取链接存为实体内容；链接的原始目标仅作为文字记录。
backup_target() {
  local dest="$1" key="$2" saved
  if [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
    return 0
  fi
  ensure_backup_dir
  saved="$BACKUP_DIR/$key"
  mkdir -p -- "$(dirname "$saved")"
  if [ -L "$dest" ]; then
    mkdir -p -- "$(dirname "$BACKUP_DIR/links/$key.target")"
    readlink -- "$dest" > "$BACKUP_DIR/links/$key.target"
  fi
  if [ -d "$dest" ]; then
    cp -aL -- "$dest" "$saved"
  elif [ -f "$dest" ]; then
    cp -pL -- "$dest" "$saved"
  elif [ ! -L "$dest" ]; then
    die "不支持的配置类型: $dest"
  fi
  log "  已备份: $dest"
}

# 先把目录链接转为实体目录，复制其中所有内容；普通目录不会整体替换。
# 递归处理父目录，防止配置仍经 ~/.config 等目录链接依赖仓库。
ensure_directory() {
  local directory="$1" parent
  [ "$directory" = / ] && return 0
  parent="$(dirname "$directory")"
  ensure_directory "$parent"
  if [ -L "$directory" ]; then
    if [ -e "$directory" ] && [ ! -d "$directory" ]; then
      die "配置父路径不是目录: $directory"
    fi
    ACTIVE_STAGE="$(mktemp -d "$parent/.dotfiles-directory.XXXXXX")"
    if [ -d "$directory" ]; then
      cp -aL -- "$directory/." "$ACTIVE_STAGE/"
    fi
    backup_target "$directory" "directories${directory}"
    ACTIVE_DEST="$directory"
    ACTIVE_OLD_LINK="$(mktemp "$parent/.dotfiles-link.XXXXXX")"
    mv -T -- "$directory" "$ACTIVE_OLD_LINK"
    mv -T -- "$ACTIVE_STAGE" "$directory"
    ACTIVE_STAGE=""
    rm -- "$ACTIVE_OLD_LINK"
    ACTIVE_OLD_LINK=""
    ACTIVE_DEST=""
    log "✓ 已转为独立目录: $directory"
  elif [ ! -d "$directory" ]; then
    mkdir -- "$directory"
  fi
}

has_linked_parent() {
  local parent
  parent="$(dirname "$1")"
  while [ "$parent" != / ]; do
    [ -L "$parent" ] && return 0
    parent="$(dirname "$parent")"
  done
  return 1
}

validate_config() {
  local src="$1" dest="$2" parent
  [ -f "$src" ] && [ -r "$src" ] || die "配置源文件缺失或不可读: $src"
  case "$dest" in
    "$REPO_DIR"|"$REPO_DIR"/*) die "部署目标不能放在仓库内: $dest" ;;
  esac
  if [ -e "$dest" ] && [ ! -f "$dest" ]; then
    die "配置目标不是普通文件: $dest"
  fi
  parent="$(dirname "$dest")"
  while [ "$parent" != / ]; do
    if [ -e "$parent" ] && [ ! -d "$parent" ]; then
      die "配置父路径不是目录: $parent"
    fi
    parent="$(dirname "$parent")"
  done
}

copy_config() {
  local src="$1" dest="$2" mode="${3:-copy}" unchanged=0
  validate_config "$src" "$dest"
  if [ "$mode" = vscode ]; then
    if [ "$(python3 "$REPO_DIR/scripts/merge_vscode_settings.py" "$src" "$dest" --check)" = unchanged ]; then
      unchanged=1
    fi
  elif cmp -s -- "$src" "$dest"; then
    unchanged=1
  fi
  if [ -f "$dest" ] && [ ! -L "$dest" ] && ! has_linked_parent "$dest" && [ "$unchanged" -eq 1 ]; then
    log "✓ 内容一致，跳过: $dest"
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      log "  [dry-run] 将备份现有配置内容及链接目标记录: $dest"
    fi
    if has_linked_parent "$dest"; then
      log "  [dry-run] 将备份并实体化父目录链接，保留目录中的额外文件"
    fi
    if [ "$mode" = vscode ]; then
      log "  [dry-run] 将合并 VS Code 光标设置并保存独立文件，保留其他设置: $dest"
    else
      log "  [dry-run] 将复制为独立文件: $src → $dest"
    fi
    return 0
  fi
  ensure_directory "$(dirname "$dest")"
  ACTIVE_STAGE="$(mktemp "$(dirname "$dest")/.dotfiles-file.XXXXXX")"
  if [ "$mode" = vscode ]; then
    python3 "$REPO_DIR/scripts/merge_vscode_settings.py" "$src" "$dest" --output "$ACTIVE_STAGE"
    # 现有设置可能含本机专用信息，保留其权限；新文件沿用 mktemp 的 0600。
    if [ -f "$dest" ]; then
      chmod --reference="$dest" "$ACTIVE_STAGE"
    fi
  else
    cp -pL -- "$src" "$ACTIVE_STAGE"
  fi
  backup_target "$dest" "files${dest}"
  # 同目录 rename：不会沿目标链接写入旧仓库，失败时原文件仍在。
  mv -T -- "$ACTIVE_STAGE" "$dest"
  ACTIVE_STAGE=""
  log "✓ 已复制为独立文件: $dest"
}

windows_config_path() {
  local win_home drive rest
  command -v cmd.exe >/dev/null 2>&1 || return 0
  win_home="$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r' || true)"
  [ -n "$win_home" ] || return 0
  if command -v wslpath >/dev/null 2>&1; then
    win_home="$(wslpath -u "$win_home" 2>/dev/null || true)"
    if [[ "$win_home" = /* ]] && [ -d "$win_home" ]; then
      printf '%s/.wslconfig\n' "$win_home"
    fi
  elif [ "${win_home:1:2}" = ':\' ]; then
    drive="$(printf '%s' "$win_home" | cut -c1 | tr 'A-Z' 'a-z')"
    rest="$(printf '%s' "$win_home" | cut -c3- | tr '\\' '/')"
    if [ -d "/mnt/$drive$rest" ]; then
      printf '/mnt/%s%s/.wslconfig\n' "$drive" "$rest"
    fi
  fi
}

main() {
  local win_dest="" wsl_changed=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1 ;;
      --skip-zed) SKIP_ZED=1 ;;
      -h|--help) usage; return 0 ;;
      *) log "未知参数: $1" >&2; usage; return 2 ;;
    esac
    shift
  done
  [[ "$CONFIG_HOME" = /* ]] || die "XDG_CONFIG_HOME 必须是绝对路径"
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  # 所有启用项在首次写入之前预检，避免源文件缺失造成半部署。
  validate_config "$REPO_DIR/.zshrc" "$HOME/.zshrc"
  validate_config "$REPO_DIR/.vimrc" "$HOME/.vimrc"
  if [ -e "$REPO_DIR/.zshrc.local" ] || [ -L "$REPO_DIR/.zshrc.local" ]; then
    validate_config "$REPO_DIR/.zshrc.local" "$HOME/.zshrc.local"
  elif [ -L "$HOME/.zshrc.local" ]; then
    validate_config "$HOME/.zshrc.local" "$HOME/.zshrc.local"
  fi
  if has_gui; then
    validate_config "$REPO_DIR/.config/Code/User/settings.json" "$CONFIG_HOME/Code/User/settings.json"
    [ -r "$REPO_DIR/scripts/merge_vscode_settings.py" ] || die "缺少 VS Code 设置合并脚本"
    command -v python3 >/dev/null 2>&1 || die "合并 VS Code 设置需要 Python 3，请手动安装: sudo apt install python3"
    python3 "$REPO_DIR/scripts/merge_vscode_settings.py" "$REPO_DIR/.config/Code/User/settings.json" "$CONFIG_HOME/Code/User/settings.json" --check >/dev/null
    if ! is_wsl; then
      validate_config "$REPO_DIR/.config/ghostty/config" "$CONFIG_HOME/ghostty/config"
    fi
    if [ "$SKIP_ZED" -eq 0 ]; then
      validate_config "$REPO_DIR/.config/zed/settings.json" "$CONFIG_HOME/zed/settings.json"
    fi
  fi
  if is_wsl; then
    [ -r "$REPO_DIR/.wslconfig" ] || die "配置源文件缺失或不可读: $REPO_DIR/.wslconfig"
    win_dest="$(windows_config_path)"
    if [ -n "$win_dest" ]; then
      validate_config "$REPO_DIR/.wslconfig" "$win_dest"
    fi
  fi

  log "== dotfiles 部署开始 =="
  [ "$DRY_RUN" -eq 0 ] || log "（dry-run 模式：仅预览，不修改任何文件）"
  log ""
  log "[1/3] 通用配置"
  # 本地扩展先就位，再部署会加载它的 .zshrc。
  if [ -e "$REPO_DIR/.zshrc.local" ] || [ -L "$REPO_DIR/.zshrc.local" ]; then
    copy_config "$REPO_DIR/.zshrc.local" "$HOME/.zshrc.local"
  elif [ -L "$HOME/.zshrc.local" ]; then
    copy_config "$HOME/.zshrc.local" "$HOME/.zshrc.local"
  fi
  copy_config "$REPO_DIR/.zshrc" "$HOME/.zshrc"
  copy_config "$REPO_DIR/.vimrc" "$HOME/.vimrc"

  log ""
  log "[2/3] 图形界面配置（Ghostty / Zed / VS Code）"
  if ! has_gui; then
    log "⏭  未检测到图形桌面，跳过 Ghostty / Zed / VS Code 配置及桌面依赖检查"
  else
    copy_config "$REPO_DIR/.config/Code/User/settings.json" "$CONFIG_HOME/Code/User/settings.json" vscode
    if is_wsl; then
      log "⏭  WSL 环境，自动跳过 Ghostty 配置"
    else
      copy_config "$REPO_DIR/.config/ghostty/config" "$CONFIG_HOME/ghostty/config"
    fi
    if [ "$SKIP_ZED" -eq 1 ]; then
      log "⏭  --skip-zed：保留本机 Zed 设置"
    else
      copy_config "$REPO_DIR/.config/zed/settings.json" "$CONFIG_HOME/zed/settings.json"
    fi
  fi

  log ""
  log "[3/3] WSL 配置（.wslconfig）"
  if ! is_wsl; then
    log "⏭  非 WSL 环境，跳过 .wslconfig 部署"
  else
    if [ -n "$win_dest" ]; then
      if [ -L "$win_dest" ] || ! cmp -s -- "$REPO_DIR/.wslconfig" "$win_dest"; then
        wsl_changed=1
      fi
      copy_config "$REPO_DIR/.wslconfig" "$win_dest"
      if [ "$wsl_changed" -eq 1 ]; then
        log "⚠️  .wslconfig 部署后需在 Windows 中手动执行 'wsl --shutdown'（请自行执行）"
      fi
    else
      log "⚠️  未能定位 Windows 用户目录，请手动复制 .wslconfig 到 Windows 用户目录"
    fi
    log "📌 Sparkle 必须手动下载安装 GUI 版本并手动配置："
    log "   手动参考 sparkle.yaml；确认代理组 openAI 与混合端口 7890"
  fi

  check_dependencies
  local login_shell
  login_shell="$(getent passwd "${USER:-$(id -un)}" | cut -d: -f7 || true)"
  if [ -n "$login_shell" ] && [ "$login_shell" != "$(command -v zsh 2>/dev/null)" ]; then
    log "ℹ️  当前登录 shell 为 $login_shell，建议执行: chsh -s \$(which zsh)（重新登录后生效）"
  fi
  log ""
  if [ "$MISSING" -eq 0 ]; then
    log "🎉 必需依赖已全部满足"
  else
    log "共 $MISSING 项必需依赖缺失：请参考上方提示手动安装（网络受限时请先开启代理）"
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log "（dry-run 结束：以上为将要执行的动作，未修改任何文件）"
  else
    log "（部署完成；配置独立于仓库。新开终端或执行 source ~/.zshrc 后生效）"
  fi
}

check_dependencies() {
  # ---------- 依赖检查（只报告，不安装） ----------
  log ""
  log "== 依赖检查（缺失项请自行安装，本脚本不会自动安装）=="

  check_cmd() {
    local name="$1" hint="$2"
    if command -v "$name" >/dev/null 2>&1; then
      log "✓ $name"
    else
      log "✗ $name —— $hint"
      MISSING=$((MISSING + 1))
    fi
  }

  check_bat() {
    if command -v batcat >/dev/null 2>&1; then
      log "✓ bat（batcat）"
    elif command -v bat >/dev/null 2>&1; then
      log "✓ bat"
    else
      log "✗ bat —— sudo apt install bat（Ubuntu 二进制名为 batcat）"
      MISSING=$((MISSING + 1))
    fi
  }

  check_cmd zsh "sudo apt install zsh；随后 chsh -s \$(which zsh) 并重新登录"
  check_cmd git "sudo apt install git"
  check_cmd vim "sudo apt install vim"
  check_bat
  check_cmd fzf "sudo apt install fzf"

  if command -v uv >/dev/null 2>&1 || [ -x "$HOME/.local/bin/uv" ]; then
    log "✓ uv"
  else
    log "✗ uv —— curl -LsSf https://astral.sh/uv/install.sh | sh（安装到 ~/.local/bin）"
    MISSING=$((MISSING + 1))
  fi

  if [ -f "$HOME/.oh-my-zsh/oh-my-zsh.sh" ]; then
    log "✓ Oh My Zsh"
  else
    log "✗ Oh My Zsh —— git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh"
    MISSING=$((MISSING + 1))
  fi

  for plugin in zsh-autosuggestions zsh-syntax-highlighting; do
    if [ -f "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/$plugin/$plugin.plugin.zsh" ] ||
       [ -f "$HOME/.oh-my-zsh/plugins/$plugin/$plugin.plugin.zsh" ]; then
      log "✓ 插件 $plugin"
    else
      log "✗ 插件 $plugin —— git clone --depth=1 https://github.com/zsh-users/$plugin.git ~/.oh-my-zsh/custom/plugins/$plugin"
      MISSING=$((MISSING + 1))
    fi
  done

  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    log "✓ NVM"
  else
    log "✗ NVM —— curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash"
    MISSING=$((MISSING + 1))
  fi

  if compgen -G "$HOME/.nvm/versions/node/*/bin/node" >/dev/null 2>&1; then
    log "✓ Node（NVM 内已安装版本）"
  else
    log "✗ Node —— nvm install --lts"
    MISSING=$((MISSING + 1))
  fi

  if command -v cargo >/dev/null 2>&1 || [ -x "$HOME/.cargo/bin/cargo" ]; then
    log "✓ Rust/cargo（可选）"
  else
    log "○ Rust/cargo 未安装（可选）—— rustup: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  fi

  if has_gui && ! is_wsl; then
    check_cmd ghostty "Ubuntu 26.04+：sudo apt install ghostty；其他版本见 https://ghostty.org/docs/install/binary"
    if command -v fc-list >/dev/null 2>&1; then
      if fc-list 2>/dev/null | grep -i "FiraCode Nerd Font" >/dev/null; then
        log "✓ 字体 FiraCode Nerd Font"
      else
        log "✗ 字体 FiraCode Nerd Font —— 从 GitHub nerd-fonts 下载 FiraCode.zip，解压到 ~/.local/share/fonts 后执行 fc-cache -fv"
        MISSING=$((MISSING + 1))
      fi
      if fc-list 2>/dev/null | grep -i "Noto Sans Mono CJK SC" >/dev/null; then
        log "✓ 字体 Noto Sans Mono CJK SC"
      else
        log "✗ 字体 Noto Sans Mono CJK SC —— sudo apt install fonts-noto-cjk"
        MISSING=$((MISSING + 1))
      fi
    else
      log "○ fontconfig 未安装，跳过字体检测 —— sudo apt install fontconfig"
    fi
  fi

  if has_gui; then
    check_cmd code "从 https://code.visualstudio.com/download 官方下载并手动安装"
    check_cmd python3 "sudo apt install python3（部署时合并 VS Code 设置使用）"
    if [ "$SKIP_ZED" -eq 0 ]; then
      check_cmd zed "从 https://zed.dev/download 官方下载，或按 https://zed.dev/docs/linux 手动安装"
    fi
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
      check_cmd wl-copy "sudo apt install wl-clipboard"
      check_cmd wl-paste "sudo apt install wl-clipboard"
    else
      check_cmd xclip "sudo apt install xclip"
    fi
  fi
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
  main "$@"
fi
