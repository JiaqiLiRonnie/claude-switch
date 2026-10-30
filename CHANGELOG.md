# Changelog

## 0.1.0 — 2026-10-30

First public release.

- `init` / `add` / `use` / `uninstall`: persistent multi-account switching by re-pointing the data-directory symlink.
- `sync`: merge the per-profile session index (newest `lastActivityAt` wins, tombstones respected, archived index rebuilt only when self-consistent); share `scratch-workspaces` and `side-session-notes`; union `git-worktrees.json`.
- `doctor` (read-only): detect sessions whose transcript exists in two `~/.claude/projects/*` folders with different content, and say which copy is complete.
- `status` (read-only).
- Every mutating command is a dry run unless `--go` is passed; overwritten files are backed up to `_backups/` (last 3 kept, older ones go to the Trash).
- 3 sandbox test suites, no real Claude install required.
- Known limitation: sidebar group / pin / star sync writes `claude_desktop_config.json`, but Claude Desktop rewrote it on next launch in our test. See README.
