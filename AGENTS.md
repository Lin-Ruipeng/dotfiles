# AGENTS.md

本仓库是个人 dotfiles（面向 WSL / Ubuntu）。交给 AI Agent 时的目标：**部署配置**，不安装任何软件。

## 执行步骤

1. 预览（先执行）：
   ```bash
   bash bootstrap.sh --dry-run
   ```
2. 正式部署：
   ```bash
   bash bootstrap.sh
   ```

`bootstrap.sh` 的行为（幂等，可反复执行）：

- 软链接 `~/.zshrc`、`~/.vimrc` 到本仓库；已存在的文件/链接先备份到 `~/.dotfiles-backup/<时间戳>/`
- 非 WSL 且检测到图形桌面（`DISPLAY` / `WAYLAND_DISPLAY`）时，才部署 `~/.config/ghostty`；WSL 或无桌面环境自动跳过
- WSL 中把 `.wslconfig` 复制到 Windows 用户目录（原文件先备份），并提示需手动 `wsl --shutdown`
- 结束时输出缺失依赖清单（含每项安装命令），供用户手动安装

## 硬性边界（不要做）

- **不要自动安装任何软件**（apt / snap / winget / 下载安装器等），除非用户明确要求
- **Sparkle 一律禁止自动安装**：必须由用户手动下载安装 GUI 版本并手动配置；`sparkle.yaml` 只做文字说明，不要尝试合并进客户端配置
- 不要 rewrite git 历史、不要 force push
- 不要删除用户文件；替换配置必须走 `bootstrap.sh` 的备份逻辑
- `wsl --shutdown` 只能提示用户手动执行（会终止 WSL 会话，也会终止你自己）

## 部署后

1. 把 `bootstrap.sh` 输出的缺失依赖清单原样展示给用户，并说明安装渠道（apt / git clone / 官方下载）
2. 提醒：新开终端或 `source ~/.zshrc` 后配置生效
3. 网络前提：中国大陆访问 GitHub 受限，安装依赖前先开代理（Windows 侧 Sparkle 监听 7890；WSL 先 `source ~/.zshrc` 再执行 `setproxy`）

## 验证

- `zsh -n .zshrc` 应无输出（语法检查）
- `bash bootstrap.sh --dry-run` 应无报错且不修改任何文件
- `ls -la ~/.zshrc ~/.vimrc` 确认指向本仓库
- 打开新 zsh 应无报错；未安装 Oh My Zsh 时会打印一条跳过提示，属预期
