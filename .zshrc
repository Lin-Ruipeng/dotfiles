# ============================================================
#  Oh My Zsh 基本配置
# ============================================================
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
# 可选主题: powerlevel10k/powerlevel10k

plugins=(git zsh-autosuggestions zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh

# ============================================================
#  用户路径 & 环境变量
# ============================================================
# 本地 bin 目录
. "$HOME/.local/bin/env"
export PATH="$HOME/.local/bin:$PATH"

# Rust 环境
. "$HOME/.cargo/env"

# ============================================================
#  别名
# ============================================================
alias bat="batcat"   # 带语法高亮的 cat

# ============================================================
#  fzf 模糊搜索配置
# ============================================================
# Ctrl+T 预览使用 batcat，右下分屏
export FZF_CTRL_T_OPTS="--preview 'batcat --style=numbers --color=always {}' --preview-window=right:60%:wrap"
# 默认底部显示，避免全屏（兼容 tmux）
export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# ============================================================
#  代理设置（适用于 WSL2 通过 Windows 主机）
# ============================================================
# 自动获取 Windows 主机 IP（每次启动时获取一次）
hostip=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
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
# opencode
export PATH="/home/muxinyue/.opencode/bin:$PATH"

# NVM（Node 版本管理）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
# 默认使用的 Node 版本路径
export PATH="$HOME/.nvm/versions/node/v24.15.0/bin:$PATH"

