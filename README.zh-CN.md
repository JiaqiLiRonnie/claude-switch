<div align="center">

# claude-switch

**macOS 上 Claude Desktop 的多账号持久切换：每个账号只登录一次，终端一条命令切换，会话列表保持一致。**

[![tests](https://github.com/JiaqiLiRonnie/claude-switch/actions/workflows/test.yml/badge.svg)](https://github.com/JiaqiLiRonnie/claude-switch/actions/workflows/test.yml)
![platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![python](https://img.shields.io/badge/python-3%20stdlib%20only-blue)
![license](https://img.shields.io/badge/license-MIT-green)

[English](README.md) · 简体中文

</div>

> **非官方项目**，与 Anthropic 无关。它只在你自己的 Mac 上移动文件夹、修改少量本地 JSON，不读取密码、Cookie 或令牌。

## 为什么需要它

Claude Desktop 同一时间只记一个登录。换账号就得退出再登录，侧边栏上下文也跟着丢。让登录“粘住”的数据（Cookie、本地存储、会话索引）都在一个目录里：`~/Library/Application Support/Claude`。

`claude-switch` 把这个目录变成**符号链接**，在 `Claude-Profiles/` 下每个账号一个目录。切换 = 退出 Claude → 改链接指向 → 重新打开。每个账号各自保留登录态，所以**每个账号只需登录一次**。

```
~/Library/Application Support/
├── Claude  ──────────────►  Claude-Profiles/work      ◀── 符号链接，原子替换
└── Claude-Profiles/
    ├── personal/      # 账号 A：Cookie、本地存储、会话索引……
    ├── work/          # 账号 B
    └── _backups/      # 被覆盖前的备份，保留最近 3 次
```

## 特性

| | |
|---|---|
| **登录持久** | 每个账号一个目录，首次登录后不用重登 |
| **默认预演** | 所有改动类命令不加 `--go` 只打印计划 |
| **会话索引合并** | 同名会话取最近活动；尊重 `deleted_<id>` 删除标记；指针冲突只报告不动；归档索引仅在自洽时才重写 |
| **不再报「Working folder no longer exists」** | `scratch-workspaces`、`side-session-notes` 在各档案间用符号链接共享 |
| **`doctor` 体检** | 只读：找出同一个会话的转录出现在两个 `~/.claude/projects/*` 文件夹且内容不同的情况，并告诉你哪份完整 |
| **默认安全** | `use` 优雅退出 Claude、从不强杀、拒绝在 Claude 内部运行；其他改动类命令在 Claude 运行时拒绝；覆盖前备份；删除进废纸篓 |
| **有测试** | 三套沙盒测试（生命周期、共享状态、doctor），用假数据目录，不需要装 Claude |
| **零依赖** | 单个 Python 3 文件，仅标准库 |

## 安装

要求：macOS、`/Applications` 里装有 Claude Desktop、Python 3、Claude 数据目录与你的主目录在同一 APFS 卷上（第一步是改名，不是复制）。

```sh
git clone https://github.com/JiaqiLiRonnie/claude-switch.git
cd claude-switch
mkdir -p ~/.local/bin && cp claude-switch ~/.local/bin/ && chmod +x ~/.local/bin/claude-switch
```

## 快速开始

> 在 **Terminal.app** 里运行，不要在 Claude 自带终端或 Claude Code 里运行。工具会检测并拒绝。

```sh
claude-switch init personal --go    # 先 Cmd+Q 退出 Claude；不加 --go 是预演
claude-switch add work --go         # 为第二个账号建空档案
claude-switch use work --go         # 首次切过去，在登录页登录一次
claude-switch use personal --go     # 之后随时免登录切换
```

完整步骤、命令表、排错见 **[使用说明](docs/USAGE.zh-CN.md)**。

## 「转录分裂」问题

项目路径里含符号链接时（例如 `/Volumes/磁盘/…` 经 `~/快捷方式` 访问），同一个会话 id 的转录文件可能同时出现在 `~/.claude/projects/` 下**两个文件夹**里：一个按符号链接路径命名，一个按真实路径命名。桌面端可能先显示旧的、被截断的那份。

我们在 Claude Desktop 代码里核实的是：恢复会话时，如果转录所在的文件夹与按会话工作目录算出的文件夹不同，桌面端会把转录**复制**到算出的文件夹，并**保留原文件**，日志里是 `Migrated transcript <id> from … to …`，于是出现两份。另外，分叉/关联会话（如 “(fork)”、“btw: …”）一开始就带着父会话转录的副本，所以它的文件里有带父会话编号的行；这和「同一个会话 id 出现在两个文件夹」是两回事。**没有核实**的是：界面在某一时刻到底读哪一份（作者先看到旧的，过一会儿才变成新的），以及保留旧副本是否是有意设计。

这是 Claude Desktop / Claude Code 本身的行为，不是本工具造成的（作者机器上 14 个分裂会话里 13 个早于本工具的安装，第 14 个出现在数据目录路径变化时），上游已有记录：
[#103806](https://github.com/anthropics/claude-code/issues/103806)、
[#98899](https://github.com/anthropics/claude-code/issues/98899)、
[#98342](https://github.com/anthropics/claude-code/issues/98342)、
[#74043](https://github.com/anthropics/claude-code/issues/74043)。

`claude-switch doctor` **只报告**。作者机器上每个分裂都是「较小的文件是较大文件的逐字节开头部分」，所以较大的那份是完整的；先备份它再做别的。经测试的自动修复在路线图里，刻意还没发布。

## 已知限制

来自真实使用的如实清单：

- **侧边栏分组/置顶/星标同步不可靠。** `sync` 会在各档案的 `claude_desktop_config.json` 之间复制，逻辑有单元测试，但作者实测 Claude Desktop 下次启动时把分组清空重写，同步没有持久效果。变通办法：在 Claude 侧边栏里重新建组。请当作实验功能。会话索引合并、共享目录、`doctor` 不受影响。
- 在 macOS 15.3.1、Claude Desktop 4.4212.0（Info.plist 显示）、Python 3.14 上用过；Claude 的磁盘布局不是公开接口，可能变化。
- 命令行提示目前只有中文。
- 真实数据上只实际用过两个档案；更多档案代码上支持，但只有测试覆盖。

## 路线图

- [ ] 英文命令行提示
- [ ] 菜单栏切换（先做成 [SwiftBar](https://github.com/swiftbar/SwiftBar) 插件调用现有 CLI，再考虑原生 App）
- [ ] 多于两个账号：真实数据端到端验证 + `list` 命令
- [ ] `doctor --fix`：经测试的转录分裂修复（合并进真实路径文件夹，另一个留作符号链接；先预演）
- [ ] 图形界面（仅当以上不够用时）
- [ ] 可靠的侧边栏分组同步（需要一条 Desktop 不会覆盖的写入路径）

## 相关项目

- [ajipurn/claude-profiles](https://github.com/ajipurn/claude-profiles)：macOS 菜单栏 App，带各档案用量显示和可选的共享历史；已被 [Agent Profiles](https://github.com/ajipurn/agent-profiles) 取代。
- [jmdarre-v/claude-multiprofile](https://github.com/jmdarre-v/claude-multiprofile)：并行运行多个 Claude Desktop / Claude Code 账号，档案相互隔离。

想要图形界面请先看它们。`claude-switch` 面向喜欢小而可审计、可脚本化、默认预演、并带「转录分裂」诊断的命令行用户。

## 开发

```sh
for t in tests/test_*.py; do python3 "$t" || exit 1; done
```

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。许可证：[MIT](LICENSE)。
