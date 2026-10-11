# ============================================================
#  Oh My Zsh 基本配置
# ============================================================
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
# 可选主题: powerlevel10k/powerlevel10k

plugins=(git)
for _plugin in zsh-autosuggestions zsh-syntax-highlighting; do
  if [ -f "${ZSH_CUSTOM:-$ZSH/custom}/plugins/$_plugin/$_plugin.plugin.zsh" ] ||
     [ -f "$ZSH/plugins/$_plugin/$_plugin.plugin.zsh" ]; then
    plugins+=("$_plugin")
  fi
done
unset _plugin

if [ -f "$ZSH/oh-my-zsh.sh" ]; then
  source "$ZSH/oh-my-zsh.sh"
else
  echo "⚠️  未检测到 Oh My Zsh（$ZSH），已跳过加载，安装方法见 dotfiles 仓库 README"
fi

# ============================================================
#  用户路径 & 环境变量
# ============================================================
# 本地 bin 目录
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
export PATH="$HOME/.local/bin:$PATH"

# Rust 环境
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# ============================================================
#  别名
# ============================================================
# 带语法高亮的 cat（Ubuntu 的 bat 包二进制名为 batcat，自动适配）
if (( $+commands[batcat] )); then
  _bat_cmd=batcat
elif (( $+commands[bat] )); then
  _bat_cmd=bat
else
  _bat_cmd=""
fi
if [ -n "$_bat_cmd" ]; then
  alias bat="$_bat_cmd"
fi

# 剪贴板：按当前桌面会话选择工具，无桌面时不设置别名
if [ -n "${WAYLAND_DISPLAY:-}" ] && (( $+commands[wl-copy] && $+commands[wl-paste] )); then
  alias cl-copy="wl-copy"
  alias cl-paste="wl-paste"
elif [ -n "${DISPLAY:-}" ] && (( $+commands[xclip] )); then
  alias cl-copy="xclip -selection clipboard"
  alias cl-paste="xclip -selection clipboard -o"
fi

# ============================================================
#  fzf 模糊搜索配置
# ============================================================
# Ctrl+T 预览使用 bat/batcat（自动选择），右下分屏
if [ -n "$_bat_cmd" ]; then
  export FZF_CTRL_T_OPTS="--preview '$_bat_cmd --style=numbers --color=always {}' --preview-window=right:60%:wrap"
fi
# 默认底部显示，避免全屏（兼容 tmux）
export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border"
# 加载 fzf 的按键绑定与补全：优先 git 安装生成的 ~/.fzf.zsh，回退到 apt 包自带示例
if [ -f ~/.fzf.zsh ]; then
  source ~/.fzf.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
  source /usr/share/doc/fzf/examples/key-bindings.zsh
  [ -f /usr/share/doc/fzf/examples/completion.zsh ] && source /usr/share/doc/fzf/examples/completion.zsh
fi

# ============================================================
#  代理设置（适用于 WSL2 通过 Windows 主机）
# ============================================================
# 镜像网络使用 localhost；其他网络模式可在 ~/.zshrc.local 中覆盖
hostip=127.0.0.1   # .wslconfig 是 mirrored 网络，WSL 直接复用 Windows 的 localhost
proxy_port=7890

alias setproxy='
    export http_proxy="http://${hostip}:${proxy_port}";
    export https_proxy="http://${hostip}:${proxy_port}";
    export all_proxy="socks5://${hostip}:${proxy_port}";
    git config --global http.proxy "http://${hostip}:${proxy_port}";
    git config --global https.proxy "http://${hostip}:${proxy_port}";
    echo -e "\033[32m✅ 代理已开启 | Windows IP: ${hostip}:${proxy_port}\033[0m";
'

alias unsetproxy='
    unset http_proxy https_proxy all_proxy;
    git config --global --unset http.proxy;
    git config --global --unset https.proxy;
    echo -e "\033[31m❌ 代理已关闭\033[0m";
'

# ============================================================
#  开发工具路径
# ============================================================
# NVM（Node 版本管理）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
# Node 版本与 PATH 由 NVM 管理，尊重 default 和当前已选择的版本。

# 本机专用配置（不随仓库分发），放在最后以便覆盖通用设置
if [ -f "$HOME/.zshrc.local" ]; then
  source "$HOME/.zshrc.local"
fi

