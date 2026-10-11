# AGENTS.md

本仓库是个人 dotfiles（面向 WSL / Ubuntu）。目标：**复制部署配置，完成后本地仓库可删除**。软件由用户自行安装。

## 执行步骤与完成条件

1. 检查现有配置及链接。存在本机专用内容时先保留：Shell 扩展放在独立的 `~/.zshrc.local`；保留完整的本机 Zed 设置时选用 `--skip-zed`。旧链接迁移及备份说明见 [README.md](README.md#旧链接迁移与备份恢复)。
2. 先预览：`bash bootstrap.sh --dry-run`。使用 `--skip-zed` 时，预览与正式部署保持相同选项。预览应无报错且不修改文件。
3. 正式部署：`bash bootstrap.sh`。所有替换通过脚本的备份与复制逻辑执行；普通文件内容一致则跳过，旧链接转换为独立副本。脚本可重复执行。
4. 验证本次部署的目标都是普通文件，父目录不经链接依赖仓库；新备份中的内容也可独立读取。确认配置内部没有加载仓库路径，才可报告部署完成、本地仓库可删除。不要主动删除用户的克隆目录。

## 环境规则

- `.zshrc` / `.vimrc` 始终部署；临时部署副本中存在 `.zshrc.local` 时一并部署。专用配置留在本机，不提交仓库。
- Ghostty 仅在非 WSL 且检测到 `DISPLAY` / `WAYLAND_DISPLAY` 时部署。
- Zed 仅在检测到图形环境时部署，包括 WSLg；无图形环境时跳过部署及依赖检查。`--skip-zed` 保留本机 Zed 设置。
- VS Code 的樱花粉色方块光标仅在图形环境部署，包括 WSLg 的 Linux GUI 客户端；用脚本合并光标条目，保留其他设置与注释，不管理 Windows 客户端或其他发行版。
- Ghostty / Zed / VS Code 使用 `${XDG_CONFIG_HOME:-$HOME/.config}`；保留配置目录中的额外文件。
- WSL 中把 `.wslconfig` 复制到 Windows 用户目录，变更后提示用户手动执行 `wsl --shutdown`。

## 硬性边界

- 配置使用独立副本，不创建指向仓库的软链接，也不通过 `source` 或其他配置引用仓库文件。
- 不自动安装软件（apt / snap / winget / 下载安装器等），除非用户明确要求。
- 用户明确要求安装 uv 时，仅使用 Astral 官方独立安装脚本：`curl -LsSf https://astral.sh/uv/install.sh | sh`。默认安装到 `~/.local/bin`，供当前用户所有项目使用；禁止通过 pip、pipx、conda 或项目虚拟环境安装 uv。
- Sparkle 一律由用户手动下载安装 GUI 版本并手动配置；`sparkle.yaml` 仅做文字说明，不自动合并客户端配置。
- 不 rewrite Git 历史，不 force push；不删除用户文件，替换前保存可恢复的备份。
- `wsl --shutdown` 只能提示用户手动执行。

## 验证与交付

- `bash -n bootstrap.sh`、`zsh -n .zshrc` 应通过；修改部署逻辑后运行 `python3 -m unittest discover -s tests -v`。
- 检查 `~/.zshrc` / `~/.vimrc` 以及本次启用的桌面配置：应存在、不是链接，内容可读取。同样检查配置的父目录和本机扩展的独立性。
- 打开新 Zsh 应无报错；未安装 Oh My Zsh 时打印跳过提示属预期。
- 把脚本输出的缺失依赖清单原样展示给用户，并说明安装渠道（apt / git clone / 官方下载）及本次备份目录。
- 提醒新开终端或 `source ~/.zshrc` 后配置生效。
- 中国大陆访问 GitHub 受限时，安装依赖前先开代理：Windows 侧 Sparkle 监听 7890；WSL 先 `source ~/.zshrc`，再执行 `setproxy`。
