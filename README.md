<div align="center">

# claude-switch

**Persistent multi-account switching for Claude Desktop on macOS — log in once per account, switch from the terminal, keep one coherent session list.**

[![tests](https://github.com/JiaqiLiRonnie/claude-switch/actions/workflows/test.yml/badge.svg)](https://github.com/JiaqiLiRonnie/claude-switch/actions/workflows/test.yml)
![platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![python](https://img.shields.io/badge/python-3%20stdlib%20only-blue)
![license](https://img.shields.io/badge/license-MIT-green)

English · [简体中文](README.zh-CN.md)

</div>

> **Unofficial.** Not affiliated with or endorsed by Anthropic. It only moves folders and edits a few local JSON files on your own Mac; it never reads passwords, cookies or tokens.
>
> **Language note:** the command-line messages are currently in Chinese. Command names and flags are English. English messages are on the [roadmap](#roadmap).

## Why

Claude Desktop keeps exactly one login. Changing account means signing out, signing in, and losing the sidebar context. The data that makes a login "stick" — cookies, local storage, session index — all lives in one directory, `~/Library/Application Support/Claude`.

`claude-switch` turns that directory into a **symlink** and keeps one directory per account under `Claude-Profiles/`. Switching = quit Claude → re-point the symlink → reopen. Each account keeps its own login, so you sign in **once per account, ever**.

```
~/Library/Application Support/
├── Claude  ──────────────►  Claude-Profiles/work      ◀── symlink, swapped atomically
└── Claude-Profiles/
    ├── personal/      # account A: cookies, local storage, session index, ...
    ├── work/          # account B
    └── _backups/      # everything claude-switch overwrote, last 3 runs kept
```

## Features

| | |
|---|---|
| **Persistent logins** | One directory per account. No re-login after the first time. |
| **Dry-run by default** | Every command that changes something only prints its plan until you add `--go`. |
| **Session index merge** | The sidebar list is per-profile. `sync` merges them: newest `lastActivityAt` wins, `deleted_<id>` tombstones are respected, conflicting pointers are reported and left untouched, archived index rebuilt only if it was self-consistent. |
| **No "Working folder no longer exists"** | `scratch-workspaces` and `side-session-notes` are shared across profiles via symlinks. |
| **`doctor`** | Read-only scan for sessions whose transcript exists in **two** `~/.claude/projects/*` folders with different content (a symlinked-path problem, see [upstream issues](#the-transcript-split-problem)). Tells you which copy is complete. |
| **Safe by construction** | `use` asks Claude to quit gracefully and never force-kills it; refuses to run from *inside* Claude; the other mutating commands refuse while Claude is running; backups before overwriting; deletions go to the Trash. |
| **Tested** | Three sandbox suites (lifecycle, shared state, doctor) on a fake data directory — no Claude install needed. |
| **Zero dependencies** | One Python 3 file, standard library only. |

## Install

Requirements: macOS, Claude Desktop in `/Applications`, Python 3, and the Claude data directory on the same APFS volume as your home folder (the first step is a rename, not a copy).

```sh
git clone https://github.com/JiaqiLiRonnie/claude-switch.git
cd claude-switch
mkdir -p ~/.local/bin && cp claude-switch ~/.local/bin/ && chmod +x ~/.local/bin/claude-switch
```

Make sure `~/.local/bin` is on your `PATH`, or run `python3 claude-switch …` from the clone.

## Quick start

> Run these in **Terminal.app**, not in Claude Desktop's built-in terminal or Claude Code — switching quits Claude and would kill the command with it. `claude-switch` detects this and refuses.

```sh
# 1. Quit Claude (Cmd+Q). Name your current account.
claude-switch init personal            # dry run: shows what would happen
claude-switch init personal --go       # do it (a rename + a symlink; instant)

# 2. Create an empty profile for the second account.
claude-switch add work --go

# 3. Switch to it. First time only: Claude opens at the login screen — sign in.
claude-switch use work --go

# 4. From now on, switching is login-free.
claude-switch use personal --go
claude-switch use work --go
```

Profile names: letters, digits, `_`, `-`, up to 32 characters. There is no limit on the number of profiles beyond disk space; `add` as many as you have accounts (tested with two on real data).

## Commands

| Command | What it does | Mutates? |
|---|---|---|
| `status` | Current profile, session counts, shared dirs, sidebar groups, whether Claude is running | no |
| `doctor` | Find transcripts duplicated across `~/.claude/projects/*` | no |
| `init <name>` | First run: rename the live data dir to profile `<name>`, put a symlink in its place | `--go` |
| `add <name>` | New empty profile; seeds `claude-code` from the current one by APFS clone (no extra space) | `--go` |
| `use <name>` | Quit Claude → merge shared state → re-point symlink → reopen Claude (`--no-launch` to skip) | `--go` |
| `sync` | Only the shared-state merge, without switching (Claude must be quit) | `--go` |
| `uninstall` | Undo: turn the current profile back into a real `Claude` directory | `--go` |

Extra flags: `--seed-vm` (also clone `vm_bundles`, ~10 GB of Cowork VM image; APFS clone costs no space until written), `--ui-from <profile>` (which profile wins for sidebar settings).

## What is shared and what is not

| Shared by `sync` / `use` | Per profile (never shared) |
|---|---|
| Session index entries `local_*.json` (merged, newest wins) | Login, cookies, local storage |
| `scratch-workspaces/`, `side-session-notes/` (one real directory, others symlink to it) | `scheduled-tasks.json` |
| `git-worktrees.json` registry (union) | Permission / security preferences |
| A small allow-list of harmless UI preferences, filled only if missing | Everything else |

## The transcript split problem

If your project folder path contains a symlink (for example `/Volumes/Disk/…` reached through `~/shortcut`), the same session id can end up with a transcript file in **two** folders under `~/.claude/projects/`: one named after the symlink path, one after the real path. Desktop may then render the older, truncated copy.

This is a Claude Desktop / Claude Code behaviour, not something `claude-switch` creates (on the author's machine 13 of the 14 split sessions pre-date setting it up; the 14th appeared when the data-directory path changed), and it is tracked upstream:
[anthropics/claude-code#103806](https://github.com/anthropics/claude-code/issues/103806),
[#98899](https://github.com/anthropics/claude-code/issues/98899),
[#98342](https://github.com/anthropics/claude-code/issues/98342),
[#74043](https://github.com/anthropics/claude-code/issues/74043).

`claude-switch doctor` only **reports**. On the author's machine every split was "the smaller file is a byte-for-byte prefix of the larger one", which makes the larger copy the complete one. Back that copy up before doing anything else. An automatic, tested repair is on the [roadmap](#roadmap); it is deliberately not shipped yet.

## Known limitations

Honest list, from real use:

- **Sidebar groups / pins / stars sync is not reliable.** `sync` copies them between profiles' `claude_desktop_config.json`, and the logic is unit-tested — but in the author's test Claude Desktop rewrote the file with an empty group list on its next launch, so the sync had no lasting effect. The workaround is to recreate groups through Claude's own sidebar. Treat this feature as experimental. Session index merge, shared directories and `doctor` are unaffected.
- Tested on macOS 15.3.1, Claude Desktop 4.4212.0 (as reported by `Info.plist`), Python 3.14. Claude's on-disk layout is not a public API and can change.
- Only the Chinese UI strings exist today.
- Two profiles were exercised on real data. More should work (all code loops over profiles) but is covered by tests only.
- `--seed-vm` and Cowork VM images are only lightly exercised.

## Safety model

- Mutating commands are dry runs unless `--go`.
- `sync` / `add` / `init` / `uninstall` refuse to run while Claude is running; `use` quits it for you, and refuses to run from inside Claude.
- Claude is asked to quit via AppleScript and given 30 s; it is **never** force-killed.
- Files that get overwritten are copied to `Claude-Profiles/_backups/<timestamp>/` first; only the last 3 runs are kept and older ones are moved to the Trash, not deleted.
- JSON that fails to parse aborts the run before anything is written.
- The symlink swap is an atomic `rename`; if `Claude` is a real directory it errors instead of clobbering it.

## Roadmap

- [ ] English CLI messages
- [ ] Menu-bar switcher (planned as an [xbar/SwiftBar](https://github.com/swiftbar/SwiftBar) plugin over the existing CLI before considering a native app)
- [ ] More than two accounts: validated end-to-end on real data, plus a `list` command
- [ ] `doctor --fix`: tested repair of transcript splits (merge into the real-path folder, keep the other as a symlink; dry run first)
- [ ] Graphical front end (only if the above proves insufficient)
- [ ] Reliable sidebar-group sync (needs a stable write path that Desktop does not overwrite)

## Related projects

- [ajipurn/claude-profiles](https://github.com/ajipurn/claude-profiles) — a macOS menu-bar app with per-profile usage display and optional shared history; now deprecated in favour of [Agent Profiles](https://github.com/ajipurn/agent-profiles).
- [jmdarre-v/claude-multiprofile](https://github.com/jmdarre-v/claude-multiprofile) — runs multiple Claude Desktop / Claude Code accounts side by side with isolated profiles.

If you want a GUI today, look there first. `claude-switch` is for people who prefer a small, auditable, scriptable CLI with dry-run semantics and a diagnostic for the transcript split.

## Development

```sh
for t in tests/test_*.py; do python3 "$t" || exit 1; done
```

See [CONTRIBUTING.md](CONTRIBUTING.md). License: [MIT](LICENSE).
