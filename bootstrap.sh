#!/usr/bin/env bash
# ============================================================
#  dotfiles 一键部署脚本
#  只部署配置，不安装任何软件；结束后输出缺失依赖清单。
#  用法:
#    bash bootstrap.sh --dry-run   # 预览将执行的动作，不改动任何文件
#    bash bootstrap.sh             # 正式部署
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="$HOME/.dotfiles-backup"
BACKUP_DIR="$BACKUP_ROOT/$(date +%Y%m%d-%H%M%S)"
DRY_RUN=0
BACKUP_NEEDED=0
MISSING=0

usage() {
  echo "用法: bash bootstrap.sh [--dry-run]"
  echo "  --dry-run   仅预览将执行的动作，不修改任何文件"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1"; usage; exit 2 ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    log "    [dry-run] $*"
  else
    "$@"
  fi
}
is_wsl()  { grep -qi microsoft /proc/version 2>/dev/null; }
has_gui() { [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; }

ensure_backup_dir() {
  if [ "$BACKUP_NEEDED" -eq 0 ]; then
    run mkdir -p "$BACKUP_DIR"
    BACKUP_NEEDED=1
    log "    备份目录: $BACKUP_DIR"
  fi
}

# 备份已存在的目标（文件/目录/链接），再创建指向仓库的软链接
link_config() {
  local src="$1" dest="$2" current=""
  if [ -L "$dest" ]; then
    current="$(readlink "$dest" 2>/dev/null || true)"
    if [ "$current" = "$src" ]; then
      log "✓ 已是本仓库链接，跳过: $dest"
      return 0
    fi
    ensure_backup_dir
    run mv "$dest" "$BACKUP_DIR/"
    log "  已备份旧链接: $dest"
  elif [ -e "$dest" ]; then
    ensure_backup_dir
    run mv "$dest" "$BACKUP_DIR/"
    log "  已备份: $dest"
  fi
  run mkdir -p "$(dirname "$dest")"
  run ln -sfn "$src" "$dest"
  log "✓ 已链接: $dest → $src"
}

# ---------- 1. 通用配置（WSL / Ubuntu 通用） ----------
log "== dotfiles 部署开始 =="
if [ "$DRY_RUN" -eq 1 ]; then
  log "（dry-run 模式：仅预览，不修改任何文件）"
fi
log ""
log "[1/3] 通用配置"
link_config "$REPO_DIR/.zshrc" "$HOME/.zshrc"
link_config "$REPO_DIR/.vimrc" "$HOME/.vimrc"

# ---------- 2. 桌面配置（仅非 WSL 且检测到图形桌面时） ----------
log ""
log "[2/3] 桌面配置（ghostty）"
if is_wsl; then
  log "⏭  WSL 环境，自动跳过桌面（ghostty）配置"
elif has_gui; then
  link_config "$REPO_DIR/.config/ghostty" "$HOME/.config/ghostty"
else
  log "⏭  未检测到图形桌面（DISPLAY / WAYLAND_DISPLAY 均为空），跳过 ghostty 配置"
fi

# ---------- 3. WSL 专属：.wslconfig + Sparkle 提示 ----------
log ""
log "[3/3] WSL 配置（.wslconfig）"
if ! is_wsl; then
  log "⏭  非 WSL 环境，跳过 .wslconfig 部署"
else
  win_home=""
  if command -v cmd.exe >/dev/null 2>&1; then
    win_home="$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r' || true)"
  fi
  if [ -n "$win_home" ] && [ "${win_home:1:2}" = ':\' ]; then
    drive="$(printf '%s' "$win_home" | cut -c1 | tr 'A-Z' 'a-z')"
    rest="$(printf '%s' "$win_home" | cut -c3- | tr '\\' '/')"
    dest="/mnt/$drive$rest/.wslconfig"
    if [ -f "$dest" ] && cmp -s "$REPO_DIR/.wslconfig" "$dest"; then
      log "✓ .wslconfig 内容一致，跳过: $dest"
    else
      if [ -f "$dest" ]; then
        ensure_backup_dir
        run cp "$dest" "$BACKUP_DIR/.wslconfig"
        log "  已备份: $dest"
      fi
      run cp "$REPO_DIR/.wslconfig" "$dest"
      log "✓ 已部署: $dest"
      log "⚠️  需在 Windows 中手动执行 'wsl --shutdown' 后生效（请自行执行）"
    fi
  else
    log "⚠️  未能定位 Windows 用户目录，请手动复制 .wslconfig 到 C:\\Users\\<你>\\"
  fi

  log ""
  log "📌 Sparkle（Windows 代理客户端）必须手动处理，脚本与 Agent 都不会自动安装："
  log "   1. 手动下载安装 GUI 版本"
  log "   2. 将 sparkle.yaml 的 prepend-rules 手动合并进 Sparkle 覆写配置"
  log "   3. 确认代理组名 openAI 与混合端口 7890（.zshrc 的 setproxy 依赖）"
fi

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

if [ -d "$HOME/.oh-my-zsh" ]; then
  log "✓ Oh My Zsh"
else
  log "✗ Oh My Zsh —— git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh"
  MISSING=$((MISSING + 1))
fi

for plugin in zsh-autosuggestions zsh-syntax-highlighting; do
  if [ -d "$HOME/.oh-my-zsh/custom/plugins/$plugin" ]; then
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

if ! is_wsl; then
  check_cmd ghostty "sudo apt install ghostty"
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
  log "（部署完成；新开终端或执行 source ~/.zshrc 后生效）"
fi
