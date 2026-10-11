# dotfiles

My personal dotfiles for shell, editor, terminal, WSL & network environment. | 个人 Shell、编辑器、终端模拟器、WSL 与网络环境配置文件集合

## 包含内容 / Contents

| 文件 | 说明 |
| --- | --- |
| [`bootstrap.sh`](bootstrap.sh) | 一键部署脚本：复制独立配置并自动备份、识别 WSL / 桌面环境、输出缺失依赖清单，支持 `--dry-run` / `--skip-zed` |
| [`AGENTS.md`](AGENTS.md) | 给 AI Agent 的部署说明与安全边界，可把仓库直接交给 Agent 自动部署 |
| [`.zshrc`](.zshrc) | Zsh 配置：Oh My Zsh、可用插件、fzf、剪贴板命令、代理开关、NVM 与 Rust/Cargo 环境，以及本机专用配置入口 |
| [`.vimrc`](.vimrc) | Vim 基础配置：显示行号、语法高亮、Tab 转 4 空格（C/C++ 为 2 空格）、自动缩进与当前行高亮 |
| [`.config/ghostty/config`](.config/ghostty/config) | Ghostty 终端配置：明暗自适应主题、Nerd Font 连字 + 中文回退、选中即复制、zsh shell 集成 |
| [`.config/Code/User/settings.json`](.config/Code/User/settings.json) | VS Code 光标配置片段：编辑区与集成终端使用樱花粉色方块光标，部署时合并并保留其他设置 |
| [`.config/zed/settings.json`](.config/zed/settings.json) | Zed 图形编辑器：字体大小、明暗主题、DeepSeek 内联助手等用户设置，不包含 Copilot 注册项或凭据 |
| [`.wslconfig`](.wslconfig) | WSL2 配置：镜像网络模式、DNS 隧道、Windows 防火墙、`autoProxy` 自动继承 Windows 代理 |
| [`sparkle.yaml`](sparkle.yaml) | Sparkle（基于 mihomo 内核的 Windows 代理客户端）的 `prepend-rules` 前置分流规则 |

## ghostty 配置说明

- **主题**：`Catppuccin Latte` / `Catppuccin Mocha` 随 GNOME 明暗模式自动切换；如需固定深色可改为 `theme = Catppuccin Mocha`。
- **字体**：`FiraCode Nerd Font Mono`（Nerd Font 连字）+ `Noto Sans Mono CJK SC` 中文回退，需自行安装对应字体。
- **交互**：樱花粉色（`#FEDFE1`）方块光标并闪烁，光标内文字为深色；选中即复制到系统剪贴板、输入时隐藏鼠标。
- **窗口**：自定义内边距与 95% 不透明度；GNOME 不支持背景模糊，`background-blur` 已注释。
- **Shell 集成**：显式 `command = /usr/bin/zsh -l` 启动登录 zsh，避免旧 GNOME 会话中 `SHELL` 残留为 bash 导致误判；保留 sudo / title / ssh-env，使用 `no-cursor` 避免输入提示处的光标被改成竖线。

> Ubuntu 的 Ghostty 启动入口可能带有 `--shell-integration-features=ssh-env`，会覆盖配置文件中的 `no-cursor`。遇到输入提示处仍显示竖线时，需要在用户级桌面入口、D-Bus 服务和 systemd 服务覆盖中移除该启动参数，让配置文件决定集成功能；随后完全退出并重新打开 Ghostty。

> 提示：`ghostty +show-config` 查看最终生效配置，`ghostty +list-themes` 查看全部内置主题，文档见 <https://ghostty.org/docs/config>。

## GUI 光标配置（VS Code / Ghostty）

两者统一使用樱花粉色 `#FEDFE1` 的方块光标，光标内文字使用深色 `#1E1E2E`。VS Code 的编辑区与集成终端均启用，失焦终端也保留方块形状；Ghostty 使用 `no-cursor` 保持方块形状，防止 Shell 集成在提示符处切换成竖线。

只有检测到 `DISPLAY` 或 `WAYLAND_DISPLAY` 时才部署并检查 GUI 依赖。VS Code 管理 Linux 稳定版的 `${XDG_CONFIG_HOME:-$HOME/.config}/Code/User/settings.json`（包括 WSLg 中运行的 Linux GUI 版本）；Ghostty 保留非 WSL 图形环境限定。Windows 客户端、Insiders 和其他配置档案不在脚本管理范围内。

VS Code 只合并仓库中的光标条目，保留其他用户设置、其他配色、JSONC 注释和尾随逗号；替换前使用统一备份逻辑。合并工具仅在部署时使用 Python 3，部署后的设置不引用仓库。配置说明见 [VS Code 官方设置文档](https://code.visualstudio.com/docs/configure/settings)。

## Zed 配置说明

检测到 `DISPLAY` 或 `WAYLAND_DISPLAY` 时才部署 Zed，包括有图形环境的 WSLg；无图形环境时跳过部署与 Zed 依赖检查。默认路径是 `~/.config/zed/settings.json`，设置了 `XDG_CONFIG_HOME` 时使用该目录。脚本只管理此文件，保留已有的主题、快捷键及其他文件。

配置保留本机字体大小（UI 24、编辑区 20）、系统明暗主题（One Light / One Dark）、DeepSeek 内联助手及 `trust_all_worktrees` 偏好。模型服务的认证需要自行配置，仓库不分发 API Key。设置与认证方式见 [Zed 官方文档](https://zed.dev/docs/configuring-zed)。

已有本机专用设置（例如 Copilot 注册项）时，用 `bash bootstrap.sh --skip-zed` 保留完整的本机 Zed 设置；后续再次部署时也使用此选项。

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

### 方式一：一键部署（推荐，可交给 Agent）

```bash
git clone https://github.com/Lin-Ruipeng/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash bootstrap.sh --dry-run   # 预览将执行的动作
bash bootstrap.sh             # 正式部署
```

- **只部署配置，不安装任何软件**；部署结束后输出缺失依赖清单与安装指引（见下方「依赖清单」）。
- **部署结果独立于仓库**：配置是普通文件，部署完成后可直接删除本地克隆目录；后续修改仓库不会自动影响已部署配置，需重新运行脚本更新。
- 幂等可重复执行；内容一致的普通文件跳过，替换前备份到 `~/.dotfiles-backup/<时间戳>.<随机后缀>/`。
- WSL 环境自动跳过桌面（ghostty）配置，并把 `.wslconfig` 复制到 Windows 用户目录，之后需在 Windows 手动执行 `wsl --shutdown` 使其生效。
- 非 WSL 且检测到图形桌面时才部署 Ghostty；图形环境中部署 Zed 和 VS Code（包括 WSLg）。三者使用 `${XDG_CONFIG_HOME:-$HOME/.config}`。
- 交给 Agent 使用：让 Agent 阅读仓库根目录的 [AGENTS.md](AGENTS.md)，按其步骤执行即可。

### 旧链接迁移与备份恢复

旧版本创建的文件链接会先备份实际内容，再换成独立文件；目录链接也会备份并实体化，保留额外文件。失效链接记录原始目标路径，再从仓库部署可用配置。不要在迁移验证完成前删除旧仓库。

备份内的 `files/<目标绝对路径去掉前导斜线>` 保存旧文件，`directories/<目标绝对路径去掉前导斜线>` 保存旧目录，`links/` 保存链接目标的文字记录。可读取的链接备份已复制实际内容，恢复不需要旧仓库。目录链接的旧配置可在目录备份内找到。

恢复前先保存当前配置，确认目标及父目录都是普通文件/目录，再将对应备份复制回原位置；不确定时让 Agent 检查备份后处理。脚本输出的备份目录是本次恢复入口。

### 本机专用配置

把本机专用 Shell 设置放在 `~/.zshrc.local`，`.zshrc` 会最后加载它。该文件应独立于仓库；可在仓库外的临时部署副本中准备 `.zshrc.local`，由脚本通过相同的备份与复制逻辑部署。仓库忽略这个同名文件，不分发本机专用配置。

剪贴板别名为 `cl-copy` / `cl-paste`：Wayland 会话使用 `wl-clipboard`，X11 会话使用 `xclip`，无桌面时不启用。Node 版本由 NVM 管理，可用 `nvm alias default <版本>` 设置默认版本。

`sparkle.yaml` 仅供用户手动参考和配置 Sparkle；脚本与 Agent 不安装客户端，也不自动合并规则。

### 依赖清单（需自行安装，仓库与脚本不会代装）

| 类别 | 软件 | 安装方式 |
| --- | --- | --- |
| 必需 | zsh | `sudo apt install zsh`，并用 `chsh -s $(which zsh)` 设为登录 shell |
| 必需 | git | `sudo apt install git` |
| 必需 | vim | `sudo apt install vim` |
| 必需 | bat | `sudo apt install bat`（Ubuntu 二进制名为 `batcat`） |
| 必需 | fzf | `sudo apt install fzf` |
| 必需 | uv | 仅使用官方独立安装脚本：`curl -LsSf https://astral.sh/uv/install.sh \| sh`（默认安装到 `~/.local/bin`，生成 `~/.local/bin/env`，供当前用户所有项目使用；安装方式限制见 [AGENTS.md](AGENTS.md#硬性边界)） |
| 必需 | Oh My Zsh | `git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh` |
| 必需 | 插件 | `git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions`（`zsh-syntax-highlighting` 同理） |
| 必需 | NVM + Node | 安装 [NVM](https://github.com/nvm-sh/nvm) 后执行 `nvm install --lts` |
| 可选 | Rust / cargo | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| 桌面（非 WSL） | ghostty | Ubuntu 26.04+：`sudo apt install ghostty`；其他版本见 [官方安装渠道](https://ghostty.org/docs/install/binary) |
| 桌面 | Zed | [官方下载](https://zed.dev/download) / [Linux 安装说明](https://zed.dev/docs/linux)，由用户手动安装 |
| 桌面 | VS Code | [官方下载](https://code.visualstudio.com/download)，由用户手动安装 |
| 桌面部署工具 | Python 3 | `sudo apt install python3`；仅用于合并 VS Code 设置 |
| 桌面 | 剪贴板工具 | Wayland：`sudo apt install wl-clipboard`；X11：`sudo apt install xclip` |
| 桌面 | FiraCode Nerd Font | 从 [nerd-fonts](https://github.com/ryanoasis/nerd-fonts) 下载 `FiraCode.zip`，解压到 `~/.local/share/fonts` 后执行 `fc-cache -fv` |
| 桌面 | Noto CJK | `sudo apt install fonts-noto-cjk` |
| Windows | Sparkle | 手动下载安装 GUI 版本并手动配置（代理组 `openAI`、混合端口 7890） |

> 注意：网络受限时（如中国大陆直连 GitHub）请先开启代理再安装依赖。WSL 镜像网络下先在 Windows 手动启动 Sparkle（混合端口 7890），再执行 `source ~/.zshrc` 和 `setproxy`。`setproxy` / `unsetproxy` 也会修改 Git 全局代理设置。

## 验证与维护

```bash
bash -n bootstrap.sh
zsh -n .zshrc
python3 -m unittest discover -s tests -v
bash bootstrap.sh --dry-run
```

回归测试仅使用临时 HOME 和配置副本，覆盖复制、旧链接迁移、独立备份、备份重名、复制失败、dry-run、WSL/桌面分支、配置目录和移走来源仓库后的可用性；测试不会安装软件或修改真实用户配置。

## License

[MIT](LICENSE) © 2026 folin (林惢朋)
