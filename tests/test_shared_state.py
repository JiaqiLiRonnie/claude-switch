#!/usr/bin/env python3
"""claude-switch 共享状态测试（目录链接 / 侧边栏分组 / 偏好补缺 / worktree 登记表），全程在临时目录。"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

SP = Path(__file__).parent
SCRIPT = SP.parent / "claude-switch"
T = Path(tempfile.mkdtemp(prefix="ss."))
ASUP, TRASH = T / "asup", T / "trash"
ASUP.mkdir(); TRASH.mkdir()
ENV = dict(os.environ, CLAUDE_SWITCH_ASUP=str(ASUP), CLAUDE_SWITCH_TRASH=str(TRASH), CLAUDE_SWITCH_TEST="1")
fails = []


def run(*args, env=None):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env or ENV)
    return r.returncode, r.stdout + r.stderr


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if (not cond and extra) else ""))
    if not cond:
        fails.append(name)


def rj(p): return json.loads(Path(p).read_text("utf-8"))


ROOT, LIVE = ASUP / "Claude-Profiles", ASUP / "Claude"
KA, KB = "acctA/orgA", "acctB/orgB"
groups = [{"id": "cg-1", "name": "① 科研总控"}, {"id": "cg-2", "name": "② 开题"}]
secs = [{"id": "pinned", "kind": "pinned"}, {"id": "routines", "kind": "routines"},
        {"id": "cg-1", "kind": "manual", "name": "① 科研总控"}, {"id": "cg-2", "kind": "manual", "name": "② 开题"},
        {"id": "sessions", "kind": "sessions"}]
plain = [{"id": "pinned", "kind": "pinned"}, {"id": "routines", "kind": "routines"}, {"id": "sessions", "kind": "sessions"}]
cfgA = {"deploymentMode": "1p", "preferences": {
    "keepAwakeEnabled": True, "bypassPermissionsModeEnabled": True, "remoteToolsDeviceName": "devA",
    "epitaxyPrefs": {
        "dframe-group-scopes": {KA: {"groups": groups, "assignments": {"code:local_s1": "cg-1", "code:local_s2": "cg-2"},
                                     "order": {"cg-1": ["code:local_s1"]}}},
        "dframe-code-sections": {KA: {"sections": secs, "migratedFrom": 1, "prefsSeeded": True},
                                 KB: {"sections": plain, "migratedFrom": 1, "prefsSeeded": True}},
        "dframe-local-slice": {"pinnedOrder": ["code:local_s2"], "homeProjectsPinnedOrder": []},
        "starred-local-code-sessions": ["code:local_s1"],
        "ccd-effort-level": "medium", "cc-landing-worktree-enabled": False,
        "cc-landing-draft-permission-mode": "bypass",   # 权限类，不应被补到别的档案
    }}}
cfgB = {"preferences": {"remoteToolsDeviceName": "devB", "epitaxyPrefs": {
    "dframe-group-scopes": {},
    "dframe-code-sections": {KB: {"sections": plain, "migratedFrom": 1, "prefsSeeded": True}},
    "dframe-local-slice": {"pinnedOrder": [], "homeProjectsPinnedOrder": []},
    "starred-local-code-sessions": [], "ccd-effort-level": "high"}}}   # b 已有 effort，不应被覆盖
wtA = {"schemaVersion": 2, "worktrees": {"w1": {"name": "w1", "createdAt": 10, "path": "/x/w1"}},
       "originPins": {"/r/.git": {"mintedAt": 5, "host": "h"}}, "untrackedDirGc": {"roots": {"A": 1}}}
wtB = {"schemaVersion": 2, "worktrees": {"w2": {"name": "w2", "createdAt": 20, "path": "/x/w2"}},
       "untrackedDirGc": {"roots": {"B": 1}}}

(ROOT / "a").mkdir(parents=True)
(ROOT / "b").mkdir()
os.symlink(ROOT / "a", LIVE)
(ROOT / "a" / "claude_desktop_config.json").write_text(json.dumps(cfgA, ensure_ascii=False, indent=2), "utf-8")
(ROOT / "b" / "claude_desktop_config.json").write_text(json.dumps(cfgB, ensure_ascii=False, indent=2), "utf-8")
(ROOT / "a" / "git-worktrees.json").write_text(json.dumps(wtA, indent="\t"), "utf-8")
(ROOT / "b" / "git-worktrees.json").write_text(json.dumps(wtB, indent="\t"), "utf-8")
(ROOT / "a" / "scratch-workspaces" / "acct" / "org" / "scratch-1").mkdir(parents=True)
(ROOT / "a" / "scratch-workspaces" / "acct" / "org" / "scratch-1" / "f.txt").write_text("hello")
(ROOT / "a" / "side-session-notes").mkdir()
(ROOT / "a" / "side-session-notes" / "local_n1").write_text("note")
(ROOT / "b" / "side-session-notes").mkdir()      # 空目录：应被替换成链接

# ---- 预演不改动 ----
snap = {p: p.read_bytes() for p in ROOT.rglob("*") if p.is_file()}
rc, out = run("sync")
check("预演不改任何文件", rc == 0 and snap == {p: p.read_bytes() for p in ROOT.rglob("*") if p.is_file()}, out)
check("预演报告 4 个文件要改（a/b 配置、a/b 的 worktree 登记）",
      "需改 4 个文件" in out, out)
check("预演提示以 a 为准", "以 a 为准" in out, out)

# ---- 执行 ----
rc, out = run("sync", "--go")
check("sync --go 成功", rc == 0, out)
for n in ("scratch-workspaces", "side-session-notes"):
    d = ROOT / "b" / n
    check(f"b/{n} 是指向 a 的相对链接", d.is_symlink() and os.readlink(d) == f"../a/{n}" and d.resolve() == (ROOT / "a" / n).resolve(), out)
check("经链接能读到 scratch 里的文件", (ROOT / "b/scratch-workspaces/acct/org/scratch-1/f.txt").read_text() == "hello")
check("经链接能读到笔记", (ROOT / "b/side-session-notes/local_n1").read_text() == "note")

b = rj(ROOT / "b" / "claude_desktop_config.json")
ep = b["preferences"]["epitaxyPrefs"]
check("b 的 B 账号拿到分组与归属", ep["dframe-group-scopes"][KB] == cfgA["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KA])
check("b 的 B 账号分区含 2 个手动分区", [s["id"] for s in ep["dframe-code-sections"][KB]["sections"]] == [s["id"] for s in secs])
check("置顶与星标已复制", ep["dframe-local-slice"]["pinnedOrder"] == ["code:local_s2"] and ep["starred-local-code-sessions"] == ["code:local_s1"])
check("界面偏好缺则补", ep.get("cc-landing-worktree-enabled") is False and b["preferences"].get("keepAwakeEnabled") is True)
check("b 已有的 effort=high 不被覆盖", ep["ccd-effort-level"] == "high")
check("权限/安全类不复制", "bypassPermissionsModeEnabled" not in b["preferences"] and "cc-landing-draft-permission-mode" not in ep)
check("b 自己的设备名保留", b["preferences"]["remoteToolsDeviceName"] == "devB")
a = rj(ROOT / "a" / "claude_desktop_config.json")
check("源档案 a 自己的 A 账号分组原样不变",
      a["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KA] == cfgA["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KA]
      and a["preferences"]["epitaxyPrefs"]["dframe-code-sections"][KA]["sections"] == secs)
check("a 里 B 账号的陈旧分区也被更新", [s["id"] for s in a["preferences"]["epitaxyPrefs"]["dframe-code-sections"][KB]["sections"]] == [s["id"] for s in secs])
check("缩进风格保持 2 空格", (ROOT / "b" / "claude_desktop_config.json").read_text("utf-8").startswith('{\n  "preferences"'))
for p, other in (("a", "w2"), ("b", "w1")):
    w = rj(ROOT / p / "git-worktrees.json")
    check(f"{p} 的 worktree 登记并集含 w1 w2", set(w["worktrees"]) == {"w1", "w2"}, str(w["worktrees"].keys()))
check("untrackedDirGc 各自保持不变", rj(ROOT / "a/git-worktrees.json")["untrackedDirGc"] == {"roots": {"A": 1}} and rj(ROOT / "b/git-worktrees.json")["untrackedDirGc"] == {"roots": {"B": 1}})
check("worktree 文件保持 tab 缩进", (ROOT / "b/git-worktrees.json").read_text("utf-8").startswith("{\n\t"))
bk = list((ROOT / "_backups").glob("*/b/claude_desktop_config.json"))
check("改动前备份了 b 的旧配置", bool(bk) and rj(bk[0])["preferences"]["epitaxyPrefs"]["dframe-group-scopes"] == {})

# ---- 幂等 ----
rc, out = run("sync", "--go")
check("再次 sync：无需改文件、无需建链接", "需改 0 个文件" in out and "需要建立链接 0 个" in out, out)

# ---- 反向：b 当前档案时改了分组，use a 应把 b 的改动带到 a ----
os.unlink(LIVE); os.symlink(ROOT / "b", LIVE)
bcfg = rj(ROOT / "b" / "claude_desktop_config.json")
gs = bcfg["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KB]
gs["groups"].append({"id": "cg-3", "name": "③ 新建"}); gs["assignments"]["code:local_s3"] = "cg-3"
(ROOT / "b" / "claude_desktop_config.json").write_text(json.dumps(bcfg, ensure_ascii=False, indent=2), "utf-8")
rc, out = run("use", "a", "--go")
check("use a 成功", rc == 0 and LIVE.resolve() == (ROOT / "a").resolve(), out)
a = rj(ROOT / "a" / "claude_desktop_config.json")["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KA]
check("b 当前档案时新增的分组带回了 a（b 为准）", [g["id"] for g in a["groups"]] == ["cg-1", "cg-2", "cg-3"] and a["assignments"].get("code:local_s3") == "cg-3", str(a))

# ---- 源为空不覆盖对方 ----
bcfg = rj(ROOT / "b" / "claude_desktop_config.json")
bcfg["preferences"]["epitaxyPrefs"]["dframe-group-scopes"] = {}
(ROOT / "b" / "claude_desktop_config.json").write_text(json.dumps(bcfg, ensure_ascii=False, indent=2), "utf-8")
os.unlink(LIVE); os.symlink(ROOT / "b", LIVE)           # b 当前，但没有分组
rc, out = run("sync", "--go")
a2 = rj(ROOT / "a" / "claude_desktop_config.json")["preferences"]["epitaxyPrefs"]["dframe-group-scopes"][KA]
check("当前档案无分组时不会清空对方，反而用 a 的补回来", rc == 0 and len(a2["groups"]) == 3 and "以 a 为准" in out, out)

# ---- 两个档案分组各不相同且当前档案无分组 -> 不替你选 ----
c = rj(ROOT / "b" / "claude_desktop_config.json")
c["preferences"]["epitaxyPrefs"]["dframe-group-scopes"] = {KB: {"groups": [{"id": "cg-9", "name": "x"}], "assignments": {}, "order": {}}}
(ROOT / "b" / "claude_desktop_config.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), "utf-8")
os.unlink(LIVE); os.symlink(ROOT / "a", LIVE)
os.mkdir(ROOT / "x"); (ROOT / "x" / "claude_desktop_config.json").write_text(json.dumps({"preferences": {"epitaxyPrefs": {}}}))
# a 当前且有分组 -> 以 a 为准，不报错
rc, out = run("sync")
check("当前档案有分组：以当前档案为准", rc == 0 and "以 a 为准" in out, out)
rc, out = run("sync", "--ui-from", "b")
check("--ui-from b 生效", rc == 0 and "以 b 为准" in out, out)
rc, out = run("sync", "--ui-from", "x")
check("--ui-from 指到没分组的档案被拒绝", rc != 0, out)

# ---- 冲突：另一档案已有非空同名目录 ----
(ROOT / "x" / "scratch-workspaces").mkdir()
(ROOT / "x" / "scratch-workspaces" / "mine.txt").write_text("keep")
rc, out = run("sync", "--go")
check("非空同名真实目录：报告冲突且不动", "手动合并" in out and (ROOT / "x/scratch-workspaces/mine.txt").read_text() == "keep" and not (ROOT / "x/scratch-workspaces").is_symlink(), out)

# ---- add 新档案：自动建共享目录链接 ----
rc, out = run("add", "c", "--go")
check("add 后新档案有 scratch-workspaces 链接", rc == 0 and (ROOT / "c/scratch-workspaces").is_symlink() and (ROOT / "c/scratch-workspaces/acct/org/scratch-1/f.txt").exists(), out)

# ---- App 运行时拒绝改配置 ----
env2 = dict(ENV, CLAUDE_SWITCH_FAKE_RUNNING="1")
rc, out = run("sync", "--go", env=env2)
check("App 运行时 sync --go 被拒绝", rc != 0, out)

# ---- 坏 JSON：中止且不改任何文件 ----
(ROOT / "b" / "claude_desktop_config.json").write_text("{not json")
snap = {p: p.read_bytes() for p in ROOT.rglob("*") if p.is_file()}
rc, out = run("sync", "--go")
check("配置不是合法 JSON：中止且不改任何文件", rc != 0 and snap == {p: p.read_bytes() for p in ROOT.rglob("*") if p.is_file()}, out)

# ---- status ----
(ROOT / "b" / "claude_desktop_config.json").write_text(json.dumps(cfgB))
rc, out = run("status")
check("status 显示共享目录与分组", rc == 0 and "共享目录 b/scratch-workspaces: 链接" in out and "侧边栏分组" in out, out)

print("\n沙盒目录:", T)
print("全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
