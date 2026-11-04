# dotfiles

My personal dotfiles for shell, editor, terminal, WSL & network environment. | 个人 Shell、编辑器、终端模拟器、WSL 与网络环境配置文件集合

## 包含内容 / Contents

| 文件 | 说明 |
| --- | --- |
| [`bootstrap.sh`](bootstrap.sh) | 一键部署：复制独立配置并备份，自动部署 NVM / Node LTS / Pi，识别 WSL / 桌面环境；支持 `--dry-run` / `--skip-zed` / `--skip-pi` |
| [`AGENTS.md`](AGENTS.md) | 给 AI Agent 的部署说明与安全边界，可把仓库直接交给 Agent 自动部署 |
| [`.zshrc`](.zshrc) | Zsh 配置：Oh My Zsh、可用插件、fzf、剪贴板命令、代理开关、NVM 与 Rust/Cargo 环境，以及本机专用配置入口 |
| [`.vimrc`](.vimrc) | Vim 基础配置：显示行号、语法高亮、Tab 转 4 空格（C/C++ 为 2 空格）、自动缩进与当前行高亮 |
| [`.config/ghostty/config`](.config/ghostty/config) | Ghostty 终端配置：明暗自适应主题、Nerd Font 连字 + 中文回退、选中即复制、zsh shell 集成 |
| [`.config/Code/User/settings.json`](.config/Code/User/settings.json) | VS Code 光标配置片段：编辑区与集成终端使用樱花粉色方块光标，部署时合并并保留其他设置 |
| [`.config/zed/settings.json`](.config/zed/settings.json) | Zed 图形编辑器：字体大小、明暗主题、DeepSeek 内联助手等用户设置，不包含 Copilot 注册项或凭据 |
| [`.wslconfig`](.wslconfig) | WSL2 配置：镜像网络模式、DNS 隧道、Windows 防火墙、`autoProxy` 自动继承 Windows 代理 |
| [`sparkle.yaml`](sparkle.yaml) | Sparkle（基于 mihomo 内核的 Windows 代理客户端）的 `+rules` 前置插入规则：Gemini 域名单独走 `🔰 节点选择` 策略组 |

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

`+rules` 为「前置插入」，会排在订阅自带规则之前，因此优先生效。当前仅保留 Gemini 专属分流：将 Gemini 相关域名从 `openAI` 组摘出，单独走 `🔰 节点选择` 策略组。

规则列表（均为 `DOMAIN-SUFFIX` 匹配，目标策略组为 `🔰 节点选择`）：

- `gemini.google.com`
- `generativelanguage.googleapis.com`
- `aida.googleapis.com`
- `ai.google.dev`

> 注意：不要用 `prepend-rules`——mihomo 与 Sparkle 都不识别该键，会被静默忽略。

> 注意：规则引用了名为 `🔰 节点选择` 的策略组，使用前请确保客户端中已存在同名代理组，或在 Sparkle 的覆写配置中调整组名。

## 使用方法 / Usage

### 方式一：一键部署（推荐，可交给 Agent）

```bash
git clone https://github.com/Lin-Ruipeng/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash bootstrap.sh --dry-run   # 预览将执行的动作
bash bootstrap.sh             # 正式部署
```

- **自动部署 NVM、最新 LTS Node.js、Pi 和指定插件**；其他软件输出缺失依赖清单与安装指引。仅复制配置时使用 `bash bootstrap.sh --skip-pi`。
- **部署结果独立于仓库**：配置是普通文件，部署完成后可直接删除本地克隆目录；后续修改仓库不会自动影响已部署配置，需重新运行脚本更新。
- 可重复执行；内容一致的普通配置文件跳过，替换前备份到 `~/.dotfiles-backup/<时间戳>.<随机后缀>/`。Pi 套件每次运行追踪最新版本。
- WSL 环境自动跳过桌面（ghostty）配置，并把 `.wslconfig` 复制到 Windows 用户目录，之后需在 Windows 手动执行 `wsl --shutdown` 使其生效。
- 非 WSL 且检测到图形桌面时才部署 Ghostty；图形环境中部署 Zed 和 VS Code（包括 WSLg）。三者使用 `${XDG_CONFIG_HOME:-$HOME/.config}`。
- 交给 Agent 使用：让 Agent 阅读仓库根目录的 [AGENTS.md](AGENTS.md)，按其步骤执行即可。

### Pi agent 自动部署

默认流程先准备 NVM 和 Node，再安装或更新 Pi、插件；有 GUI 时注册 Context7。`--skip-pi` 跳过这一整套变更；`--dry-run` 只显示计划，不联网、不加载 NVM、不运行 Pi CLI，也不创建锁或刷新凭据。

**NVM 与 Node：**缺少 `~/.nvm/nvm.sh` 时运行 [NVM 官方安装脚本](https://github.com/nvm-sh/nvm#install--update-script)（当前采用 v0.40.8），用 `PROFILE=/dev/null` 避免追加 Shell 配置；仓库的 `.zshrc` 已负责加载 NVM。成功新装后输出“已帮你安装 NVM”。已有 NVM 复用，每次执行 `nvm install --lts`、`nvm use --lts`，并用 `nvm alias default <此次具体版本>` 设置默认值；旧 Node 版本保留。安装过程需要 curl，缺失时按提示手动准备。

**Pi：**首次使用 [官网](https://pi.dev/) 的命令，在没有控制终端、输出不是 TTY 的子进程中执行，避免安装器启动交互会话：

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

已有官方管理安装执行 `pi update --no-approve`。插件逐个执行 `pi install npm:<包名> --no-approve`，受管理插件的旧版本锁定会被替换为最新版；用户额外插件及项目局部配置保留。Pi 配置使用 `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}`，独立于 `XDG_CONFIG_HOME`；安装及配置目录应位于仓库外。

| 环境 | 自动安装并更新的计划插件 | Context7 |
| --- | --- | --- |
| `DISPLAY` 或 `WAYLAND_DISPLAY` 非空，包括 WSLg | `@plannotator/pi-extension` | 自动注册，用户手动登录 |
| 无图形环境 | `pi-plan` | 跳过注册，已有 MCP 配置保留 |

两种环境都安装并更新 `@juicesharp/rpiv-ask-user-question`、`@juicesharp/rpiv-todo`、`pi-subagents`、`pi-web-access`、`pi-extmgr`。已存在的另一种计划插件保留安装，备份后禁用 extensions、skills、prompts、themes 全部资源，避免残留技能与快捷键冲突；当前选中的计划插件启用。

GUI 分支在 Context7 缺失或配置不一致时，先保存备份，再使用以下命令统一 URL 和暴露方式；其他 MCP 服务和登录凭据保留：

```bash
pi mcp add context7 --url https://mcp.context7.com/mcp --exposure direct
```

注册通过临时配置完成，成功后以独立文件部署。部署脚本会提醒用户手动执行下面的授权命令，不会自动打开登录页面：

```bash
pi mcp login context7
```

**终端规划限制：**当前原版 [pi-plan](https://github.com/zx06/pi-packages/tree/main/packages/plan) 可用 `/plan`、`/plan:status`、`Ctrl+Alt+P` 或 `pi --plan` 操作，审批在终端内完成。已核查的 0.2.0 版本在规划时只启用 `read/bash/grep/find/ls`，退出或执行时改为 `read/bash/edit/write`；不会自动恢复问答、todo、联网、子代理等额外工具。仓库按原版安装，未维护兼容补丁；后续更新以插件实际行为为准。

**失败与迁移：**单个插件失败后继续其他独立项；NVM、Node 或 Pi 等前置失败则跳过依赖项。末尾汇总成功、失败、跳过项、备份目录和重试方法，有失败时返回非零状态；等待手动登录属于正常待办。已有非官方管理 Pi 时，脚本提示先手动使用官网安装器迁移，不代为卸载旧安装。

如果旧 Pi 私有 Node 入口会覆盖 NVM，先将其内容备份，再把入口移入本次备份的 `retired/` 下，保留原运行时版本目录。恢复时使用独立内容备份，链接原目标只作为文字记录。同一轮部署反复修改同一文件时保留最初备份。

### 旧链接迁移与备份恢复

旧版本创建的文件链接会先备份实际内容，再换成独立文件；目录链接也会备份并实体化，保留额外文件。失效链接记录原始目标路径，再从仓库部署可用配置。不要在迁移验证完成前删除旧仓库。

备份内的 `files/<目标绝对路径去掉前导斜线>` 保存旧文件，`directories/<目标绝对路径去掉前导斜线>` 保存旧目录，`links/` 保存链接目标的文字记录。可读取的链接备份已复制实际内容，恢复不需要旧仓库。目录链接的旧配置可在目录备份内找到。

恢复前先保存当前配置，确认目标及父目录都是普通文件/目录，再将对应备份复制回原位置；不确定时让 Agent 检查备份后处理。脚本输出的备份目录是本次恢复入口。

### 本机专用配置

把本机专用 Shell 设置放在 `~/.zshrc.local`，`.zshrc` 会最后加载它。该文件应独立于仓库；可在仓库外的临时部署副本中准备 `.zshrc.local`，由脚本通过相同的备份与复制逻辑部署。仓库忽略这个同名文件，不分发本机专用配置。

剪贴板别名为 `cl-copy` / `cl-paste`：Wayland 会话使用 `wl-clipboard`，X11 会话使用 `xclip`，无桌面时不启用。Node 版本由 NVM 管理，可用 `nvm alias default <版本>` 设置默认版本。

`sparkle.yaml` 仅供用户手动参考和配置 Sparkle；脚本与 Agent 不安装客户端，也不自动合并规则。

### 依赖清单

NVM / Node / Pi 由默认部署流程管理，其余依赖需自行安装。使用 `--skip-pi` 时也跳过 NVM 和 Node 的安装与更新。

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
| 自动管理 | NVM + Node LTS | 默认部署自动准备；缺少 NVM 时明确提示新装结果，最新 LTS 具体版本设为 default |
| 自动管理 | Pi + 指定插件 | 官网 curl 首装，后续更新；环境分支与 Context7 登录见上方说明 |
| Pi 安装工具 | curl / setsid | `sudo apt install curl util-linux`；setsid 用于隔离官网安装器交互，脚本不代装 |
| 可选 | Rust / cargo | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| 桌面（非 WSL） | ghostty | Ubuntu 26.04+：`sudo apt install ghostty`；其他版本见 [官方安装渠道](https://ghostty.org/docs/install/binary) |
| 桌面 | Zed | [官方下载](https://zed.dev/download) / [Linux 安装说明](https://zed.dev/docs/linux)，由用户手动安装 |
| 桌面 | VS Code | [官方下载](https://code.visualstudio.com/download)，由用户手动安装 |
| 桌面部署工具 | Python 3 | `sudo apt install python3`；仅用于合并 VS Code 设置 |
| 桌面 | 剪贴板工具 | Wayland：`sudo apt install wl-clipboard`；X11：`sudo apt install xclip` |
| 桌面 | FiraCode Nerd Font | 从 [nerd-fonts](https://github.com/ryanoasis/nerd-fonts) 下载 `FiraCode.zip`，解压到 `~/.local/share/fonts` 后执行 `fc-cache -fv` |
| 桌面 | Noto CJK | `sudo apt install fonts-noto-cjk` |
| Windows | Sparkle | 手动下载安装 GUI 版本并手动配置（代理组 `🔰 节点选择`、混合端口 7890） |

> 注意：网络受限时（如中国大陆直连 GitHub）请先开启代理再安装依赖。WSL 镜像网络下先在 Windows 手动启动 Sparkle（混合端口 7890），再执行 `source ~/.zshrc` 和 `setproxy`。`setproxy` / `unsetproxy` 也会修改 Git 全局代理设置。

## 验证与维护

```bash
bash -n bootstrap.sh
bash -n scripts/setup_pi.sh
zsh -n .zshrc
node --check scripts/pi_settings.js
python3 -m unittest discover -s tests -v
bash bootstrap.sh --dry-run
```

回归测试使用临时 HOME、配置副本及 NVM / curl / Pi 命令替身，覆盖配置复制、独立备份、Pi 安装与更新、GUI/终端分支、规划插件禁用、MCP 注册与失败、dry-run 及移走来源仓库后的可用性；测试不会下载软件、登录账户或修改真实用户配置。Node 用于运行 Pi 配置合并工具的测试。

## License

[MIT](LICENSE) © 2026 folin (林惢朋)
