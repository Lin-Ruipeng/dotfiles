# dotfiles

面向 WSL / Ubuntu 的 Shell、编辑器、终端和网络配置。Agent 的部署入口见 [AGENTS.md](AGENTS.md)。

## 一键部署

```bash
git clone https://github.com/Lin-Ruipeng/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash bootstrap.sh --dry-run
bash bootstrap.sh
```

预览和正式部署使用相同的 `--skip-zed` 或 `--skip-pi` 选项。验证配置和备份均可独立使用后即可移走克隆目录。更新配置时重新运行脚本。

### 配置目标

图形环境由非空的 `DISPLAY` 或 `WAYLAND_DISPLAY` 判定。下表的配置目录为 `${XDG_CONFIG_HOME:-$HOME/.config}`。桌面依赖随对应配置启用。

| 源文件 | 部署条件与目标 |
| --- | --- |
| [`.zshrc`](.zshrc) | 始终复制到 `~/.zshrc` |
| [`.vimrc`](.vimrc) | 始终复制到 `~/.vimrc` |
| [Ghostty](.config/ghostty/config) | 非 WSL 图形环境，复制到配置目录的 `ghostty/config` |
| [VS Code](.config/Code/User/settings.json) | 图形环境（含 WSLg），合并到 Linux 稳定版的 `Code/User/settings.json` |
| [Zed](.config/zed/settings.json) | 图形环境（含 WSLg），复制到 `zed/settings.json`。用 `--skip-zed` 保留整份本机设置 |
| [`.wslconfig`](.wslconfig) | WSL 中复制到 Windows 用户目录。变更后由用户在 Windows 执行 `wsl --shutdown` |

### 桌面配置

- **光标**。Ghostty 和 VS Code 使用樱花粉色 `#FEDFE1` 方块光标及深色 `#1E1E2E` 光标内文字。VS Code 只合并光标条目，保留其他设置、JSONC 注释和尾随逗号。合并需要 Python 3。
- **Ghostty**。随系统明暗切换 Catppuccin Latte / Mocha。使用 FiraCode Nerd Font Mono 和 Noto Sans Mono CJK SC。用 `ghostty +show-config` 查看生效配置，`ghostty +list-themes` 查看内置主题。若 Ubuntu 启动入口带有 `--shell-integration-features=ssh-env`，它会覆盖文件里的 `no-cursor`。输入提示处仍是竖线时，在用户级桌面入口、D-Bus 服务和 systemd 服务的覆盖配置中移除该启动参数，然后重新打开 Ghostty。 [官方配置文档](https://ghostty.org/docs/config)
- **Zed**。模板设置 UI 字号 24、编辑区字号 20、One Light / One Dark 主题和 DeepSeek 内联助手。脚本替换 `settings.json`，保留目录中的独立主题文件、键位文件和其他文件。模型服务认证在本机配置。 [官方配置文档](https://zed.dev/docs/configuring-zed)

### Pi agent 自动部署

默认准备 NVM、Node、Pi 和插件。`--skip-pi` 跳过整个阶段，包括 Context7 与 Pi 用户级指令。

**NVM 与 Node**。缺少 `~/.nvm/nvm.sh` 时使用 [NVM 官方安装脚本](https://github.com/nvm-sh/nvm#install--update-script) v0.40.8，设置 `PROFILE=/dev/null`。`.zshrc` 负责加载 NVM。部署执行 `nvm install --lts`、`nvm use --lts`，再用 `nvm alias default <此次具体版本>` 设为默认，保留已有 Node 版本。

**Pi**。首次部署只用官网安装命令，由脚本在无交互终端的子进程中执行。

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

已有官方管理安装用 `pi update --no-approve`。发现其他来源的 Pi 时，先由用户用官网安装器迁移，再重跑部署。

Pi 使用 `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}`，并将仓库的 [Pi 用户级指令](.pi/agent/AGENTS.md) 复制为该目录下的 `AGENTS.md`。安装、配置目录及官方安装内部链接的目标须在仓库外。

| 环境 | 规划插件 | Context7 |
| --- | --- | --- |
| 图形环境（含 WSLg） | `@plannotator/pi-extension` | 注册 |
| 无图形环境 | `pi-plan` | 保留已有 MCP 配置 |

两个分支都管理 `@juicesharp/rpiv-ask-user-question`、`pi-subagents`、`pi-web-access`、`pi-extmgr`。备份并合并 `settings.json` 后，用 `pi install npm:<包名> --no-approve` 逐个更新受管理插件。保留用户额外插件和项目设置。另一种规划插件如已安装，禁用其 extensions、skills、prompts、themes。

Context7 缺失或配置不一致时，脚本在临时配置中运行注册命令。成功后备份原文件并部署新配置，保留其他 MCP 服务及本机凭据。

```bash
pi mcp add context7 --url https://mcp.context7.com/mcp --exposure direct --no-approve
```

用户在本机完成登录。

```bash
pi mcp login context7
```

**终端规划**。[`pi-plan`](https://github.com/zx06/pi-packages/tree/main/packages/plan) 可用 `/plan`、`/plan:status`、`Ctrl+Alt+P` 或 `pi --plan`，在终端完成审批。0.2.0 版规划时启用 `read/bash/grep/find/ls`，退出或执行时切换到 `read/bash/edit/write`。问答、联网和子代理等额外工具需另行恢复。

**失败处理**。单个插件失败后继续其他独立项，前置步骤失败则跳过依赖项。查看末尾汇总及备份目录，修复后重跑。有失败时返回非零状态。

Pi 私有 Node 入口会影响 NVM 选中的版本。脚本备份该入口并移入本次备份的 `retired/`，保留原运行时版本目录。恢复时用备份中的独立副本。

### 旧链接迁移与备份恢复

脚本把目标及其父目录中的链接转换为独立副本，保留目录里的额外文件。相同内容的普通配置文件直接跳过。变更前将最初的内容保存到 `~/.dotfiles-backup/<时间戳>.<随机后缀>/`。

备份的 `files/` 和 `directories/` 按目标绝对路径保存可独立读取的内容，`links/` 记录链接原目标，包括失效链接。恢复时先保存当前配置并核对目标及父目录，再从脚本报告的备份目录把对应内容复制回原位置。

### 本机专用配置

`.zshrc` 最后加载 `~/.zshrc.local`。需要随脚本复制本机扩展时，把它放在仓库外的临时部署副本根目录。

剪贴板别名为 `cl-copy` 和 `cl-paste`。Wayland 会话用 `wl-clipboard`，X11 会话用 `xclip`。

### 依赖清单

| 类别 | 软件 | 安装方式 |
| --- | --- | --- |
| 必需 | zsh | `sudo apt install zsh`，用 `chsh -s $(which zsh)` 设为登录 Shell |
| 必需 | git | `sudo apt install git` |
| 必需 | vim | `sudo apt install vim` |
| 必需 | bat | `sudo apt install bat`（Ubuntu 二进制名为 `batcat`） |
| 必需 | fzf | `sudo apt install fzf` |
| 必需 | uv | Astral 官方独立安装脚本 `curl -LsSf https://astral.sh/uv/install.sh \| sh`，默认装到 `~/.local/bin` 供当前用户使用 |
| 必需 | Oh My Zsh | `git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh` |
| 必需 | 插件 | `git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions`（`zsh-syntax-highlighting` 同理） |
| Pi 安装工具 | curl / setsid | `sudo apt install curl util-linux` |
| 可选 | Rust / cargo | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| 桌面（非 WSL） | ghostty | Ubuntu 26.04+ 用 `sudo apt install ghostty`，其他版本见[官方安装渠道](https://ghostty.org/docs/install/binary) |
| 桌面 | Zed | [官方下载](https://zed.dev/download) / [Linux 安装说明](https://zed.dev/docs/linux) |
| 桌面 | VS Code | [官方下载](https://code.visualstudio.com/download) |
| 桌面部署工具 | Python 3 | `sudo apt install python3` |
| 桌面 | 剪贴板工具 | Wayland 用 `sudo apt install wl-clipboard`，X11 用 `sudo apt install xclip` |
| Ghostty | FiraCode Nerd Font | 从 [nerd-fonts](https://github.com/ryanoasis/nerd-fonts) 下载 `FiraCode.zip`，解压到 `~/.local/share/fonts` 后执行 `fc-cache -fv` |
| Ghostty | Noto CJK | `sudo apt install fonts-noto-cjk` |

## Sparkle 代理

在 Windows 手动安装 Sparkle GUI，设置混合端口 7890，并在覆写配置中使用 [sparkle.yaml](sparkle.yaml)。`+rules` 将 Gemini 分流规则放在订阅规则之前。客户端的代理组名需与规则中的 `🔰 节点选择` 一致。

网络受限时，在安装依赖前启动代理。WSL 镜像网络下，Windows 侧启动 Sparkle 后，在 WSL 执行 `source ~/.zshrc` 和 `setproxy`。`setproxy` 和 `unsetproxy` 也会修改 Git 全局代理设置。

## 验证与维护

```bash
bash -n bootstrap.sh
bash -n scripts/setup_pi.sh
zsh -n .zshrc
node --check scripts/pi_settings.js
python3 -m unittest discover -s tests -v
```

回归测试使用临时 HOME 和命令替身。Pi 配置合并测试需要 Node。

## License

[MIT](LICENSE) © 2026 folin (林惢朋)
