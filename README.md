# dotfiles

My personal dotfiles for shell, editor, terminal, WSL & network environment. | 个人 Shell、编辑器、终端模拟器、WSL 与网络环境配置文件集合

## 包含内容 / Contents

| 文件 | 说明 |
| --- | --- |
| [`.zshrc`](.zshrc) | Zsh 配置：Oh My Zsh（robbyrussell 主题）、`git` / `zsh-autosuggestions` / `zsh-syntax-highlighting` 插件、fzf 模糊搜索、代理开关别名、NVM 与 Rust/Cargo 环境变量 |
| [`.vimrc`](.vimrc) | Vim 基础配置：显示行号、语法高亮、Tab 转 4 空格（C/C++ 为 2 空格）、自动缩进与当前行高亮 |
| [`.config/ghostty/config`](.config/ghostty/config) | Ghostty 终端配置：明暗自适应主题、Nerd Font 连字 + 中文回退、选中即复制、zsh shell 集成 |
| [`.wslconfig`](.wslconfig) | WSL2 配置：镜像网络模式、DNS 隧道、Windows 防火墙、`autoProxy` 自动继承 Windows 代理 |
| [`sparkle.yaml`](sparkle.yaml) | Sparkle（基于 mihomo 内核的 Windows 代理客户端）的 `prepend-rules` 前置分流规则 |

## ghostty 配置说明

- **主题**：`Catppuccin Latte` / `Catppuccin Mocha` 随 GNOME 明暗模式自动切换；如需固定深色可改为 `theme = Catppuccin Mocha`。
- **字体**：`FiraCode Nerd Font Mono`（Nerd Font 连字）+ `Noto Sans Mono CJK SC` 中文回退，需自行安装对应字体。
- **交互**：块状光标并闪烁、选中即复制到系统剪贴板、输入时隐藏鼠标。
- **窗口**：自定义内边距与 95% 不透明度；GNOME 不支持背景模糊，`background-blur` 已注释。
- **Shell 集成**：显式 `command = /usr/bin/zsh -l` 启动登录 zsh，避免旧 GNOME 会话中 `SHELL` 残留为 bash 导致误判；集成功能为 cursor / sudo / title。

> 提示：`ghostty +show-config` 查看最终生效配置，`ghostty +list-themes` 查看全部内置主题，文档见 <https://ghostty.org/docs/config>。

## sparkle.yaml 规则说明

按优先级从高到低：

1. **远程控制直连**：`UURemote.exe`、`uuycmgr.exe`、`GameViewer.exe` 进程走 `DIRECT`，避免远程桌面被代理断开。
2. **Codex 客户端接管**：`codex.exe` 走 `openAI` 策略组。
3. **禁用 QUIC**：`UDP-PORT,443` 直接 `REJECT`，强制后续流量走更稳定的 TCP 代理。
4. **Gemini 域名**：`gemini.google.com`、`generativelanguage.googleapis.com`、`ai.google.dev` 走 `openAI` 策略组。
5. **Google 及依赖资源**：`google.com`、`googleapis.com`、`gstatic.com`、`googleusercontent.com` 走 `openAI` 策略组。
6. **兜底规则**：`DOMAIN-KEYWORD,google` 走 `openAI` 策略组。

> 注意：规则引用了名为 `openAI` 的策略组，使用前请确保客户端中已存在同名代理组，或在 Sparkle 的覆写配置中调整组名。

## 使用方法 / Usage

克隆仓库：

```bash
git clone https://github.com/Lin-Ruipeng/dotfiles.git ~/dotfiles
```

软链接 Linux / WSL 侧配置（已存在的配置请先备份）：

```bash
ln -sf ~/dotfiles/.zshrc ~/.zshrc
ln -sf ~/dotfiles/.vimrc ~/.vimrc
ln -sf ~/dotfiles/.config/ghostty ~/.config/ghostty
```

> 注意：若 `~/.config/ghostty` 已存在，需先备份并删除该目录再执行软链接，否则会在原目录内创建嵌套链接。

WSL 配置需放到 Windows 用户目录（在 WSL 中执行，把 `<WindowsUser>` 换成实际用户名）：

```bash
cp ~/dotfiles/.wslconfig /mnt/c/Users/<WindowsUser>/.wslconfig
```

修改 `.wslconfig` 后需在 Windows 中执行 `wsl --shutdown` 重启 WSL 生效。

`sparkle.yaml` 为 Sparkle 覆写配置片段：可直接放入 Sparkle 的覆写/配置目录，或将 `prepend-rules` 内容合并到现有客户端配置中。

## License

[MIT](LICENSE) © 2026 folin (林惢朋)
