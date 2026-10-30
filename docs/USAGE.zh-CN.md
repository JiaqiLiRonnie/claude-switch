# claude-switch 使用说明（简体中文）

> 目的：让 Claude Desktop 里的多个账号**各登录一次，之后一条命令切换**，侧边栏会话列表保持一致。
> 所有命令都在 **Terminal.app** 里运行（不要在 Claude 自带终端或 Claude Code 里运行，切换会退出 Claude，把命令一起杀掉）。
> 改动类命令**默认只预演**，确认无误后加 `--go` 才真正执行。

## 0. 安装（一次）

```sh
git clone https://github.com/JiaqiLiRonnie/claude-switch.git
cd claude-switch
mkdir -p ~/.local/bin && cp claude-switch ~/.local/bin/ && chmod +x ~/.local/bin/claude-switch
```

`~/.local/bin` 不在 PATH 里的话，把下面所有 `claude-switch` 换成 `python3 claude-switch`（在仓库目录里运行）。

## 1. 首次设置（一次）

1. Cmd+Q **完全退出** Claude Desktop。
2. 给当前账号起个名字（字母/数字/`_`/`-`，最长 32 位），先预演再执行：

```sh
claude-switch init personal
claude-switch init personal --go
```

这一步只是把 `~/Library/Application Support/Claude` 改名成 `Claude-Profiles/personal`，再在原位放一个符号链接。同一磁盘上改名，瞬间完成，不复制数据。

3. 为第二个账号建空档案：

```sh
claude-switch add work --go
```

## 2. 日常切换

```sh
claude-switch use work --go        # 切到 work
claude-switch use personal --go    # 切回 personal
```

- 第一次切到一个新档案时，Claude 会停在登录页，**登录一次**，以后不用再登。
- 会自动：退出 Claude → 合并各档案的会话列表 → 改链接 → 重新打开 Claude。
- 不想自动打开：加 `--no-launch`。
- 想先看看会发生什么：去掉 `--go`。

## 3. 其他命令

| 命令 | 作用 |
|---|---|
| `claude-switch status` | 看当前档案、各档案会话数、共享目录、侧边栏分组、Claude 是否在运行（只读） |
| `claude-switch doctor` | 体检：找出同一个会话的转录出现在两个文件夹且内容不同的情况（只读） |
| `claude-switch sync --go` | 不切换，只合并共享状态（需先退出 Claude） |
| `claude-switch add 名字 --seed-vm --go` | 新建档案时连 Cowork 虚拟机镜像（约 10GB）一起克隆（APFS 克隆，写入前不占空间） |
| `claude-switch uninstall --go` | 还原：把当前档案改回真实的 `Claude` 目录，其他档案留在 `Claude-Profiles` |

## 4. 它会共享什么、不共享什么

- **共享**：会话列表（同名会话取最近活动那份，尊重删除标记，指针冲突的只报告不动）、无文件夹会话的工作目录和笔记、worktree 登记表、少量无害的界面偏好（只补缺）。
- **不共享**：登录态、Cookie、本地存储、定时任务、权限/安全类设置。

## 5. 出问题时

| 现象 | 处理 |
|---|---|
| 提示「还在运行」 | Cmd+Q 完全退出 Claude（菜单栏图标也要退），再运行 |
| 提示「从 Claude 里面运行」 | 换到 Terminal.app 运行 |
| 提示「Working folder no longer exists」 | 先 `claude-switch sync`（预演），确认后 `--go`，让共享目录链接建起来 |
| 切换后侧边栏分组没了 | 已知限制：分组同步目前不可靠，Claude 启动时会覆盖。在侧边栏里重新建组 |
| 同一个会话打开时先显示旧内容、过一会儿又变新 | 多半是「转录分裂」：运行 `claude-switch doctor`，较大的那份是完整的，**先备份它**。目前工具只报告，不自动修复 |
| 想完全恢复成没装过的样子 | 退出 Claude，`claude-switch uninstall --go` |

## 6. 它改了哪里、能不能找回

- 被覆盖的文件，先复制到 `~/Library/Application Support/Claude-Profiles/_backups/<时间>/`，保留最近 3 次；更旧的进废纸篓，不是直接删除。
- 工具从不强制结束 Claude；30 秒内没退出就停下，让你手动退出。
- 任何 JSON 解析失败都会在写入前中止。

## 7. 已知限制（如实）

- 命令行提示目前是中文。
- 在 macOS 15.3.1、Claude Desktop 4.4212.0（Info.plist 显示）、Python 3.14 上用过；Claude 的磁盘布局不是公开接口，可能随版本变化。
- 真实数据上只实际用过两个档案。
- 侧边栏分组/置顶/星标同步不可靠（见上）。
