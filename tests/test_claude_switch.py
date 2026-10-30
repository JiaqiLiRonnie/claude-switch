#!/usr/bin/env python3
"""claude-switch 沙盒生命周期测试：全程在临时目录里，不碰真实数据，不启动/退出真实 App。"""
import json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

SP = Path(__file__).parent
SCRIPT = SP.parent / "claude-switch"
T = Path(tempfile.mkdtemp(prefix="cs."))
ASUP, TRASH = T / "asup", T / "trash"
ASUP.mkdir(); TRASH.mkdir()
ENV = dict(os.environ, CLAUDE_SWITCH_ASUP=str(ASUP), CLAUDE_SWITCH_TRASH=str(TRASH), CLAUDE_SWITCH_TEST="1")
fails = []

def run(*args, env=None):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env or ENV)
    return r.returncode, r.stdout + r.stderr

def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if (not cond and extra) else ""))
    if not cond: fails.append(name)

def wj(p, **kw):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(kw))
def rj(p): return json.loads(Path(p).read_text())

LIVE, ROOT = ASUP / "Claude", ASUP / "Claude-Profiles"
# ---- 构造「现有数据目录」：账号A ----
LIVE.mkdir()
wj(LIVE / "config.json", login="A")
(LIVE / "claude-code").mkdir(); (LIVE / "claude-code" / "x.bin").write_bytes(b"cli")
(LIVE / "vm_bundles").mkdir()
with open(LIVE / "vm_bundles" / "big.img", "wb") as f:
    for _ in range(120): f.write(os.urandom(1_000_000))
oa = LIVE / "claude-code-sessions" / "acctA" / "orgA"
wj(oa / "local_s1.json", lastActivityAt=2000, cliSessionId="c1", isArchived=False)
wj(oa / "local_s2.json", lastActivityAt=1000, cliSessionId="c2", isArchived=False)
wj(oa / "local_s3.json", lastActivityAt=3000, cliSessionId="c3", isArchived=True)
wj(oa / "local_sX.json", lastActivityAt=700, cliSessionId="cx", isArchived=False)
wj(oa / "local_t1.json", lastActivityAt=500, cliSessionId="cA", isArchived=False)
(oa / "archived-sessions.idx").write_text(json.dumps({"v": 1, "archived": ["local_s3"]}, separators=(",", ":")))
(oa / "scheduled-tasks.json").write_text("A-tasks")
(oa / "claude-code-sessions_backup_x").mkdir()   # 名字含 _backup 的子目录不应被当作会话目录

# 1 预演不改动
rc, out = run("init", "main")
check("init 预演不改动", rc == 0 and LIVE.is_dir() and not LIVE.is_symlink() and not ROOT.exists(), out)
# 2 init
rc, out = run("init", "main", "--go")
check("init --go 后 Claude 是符号链接且数据可读", rc == 0 and LIVE.is_symlink() and rj(LIVE / "config.json")["login"] == "A", out)
check("真实目录已改名到档案下", (ROOT / "main" / "config.json").exists())
rc, out = run("init", "other", "--go")
check("重复 init 被拒绝", rc != 0, out)
# 3 非法名字
for bad in ["../x", "_bad", "", "a b", "a/b", "-x"]:
    rc, _ = run("add", bad, "--go") if bad else run("add", "--go")
    check(f"非法档案名被拒绝 {bad!r}", rc != 0)
# 4 add（含 APFS 克隆）
rc, out = run("add", "second", "--go", "--seed-vm")
m = re.search(r"约 (\d+) MB", out)
used = int(m.group(1)) if m else -1
check("add 成功", rc == 0 and (ROOT / "second").is_dir(), out)
check("克隆内容一致", (ROOT / "second/vm_bundles/big.img").read_bytes()[:1000000] == (ROOT / "main/vm_bundles/big.img").read_bytes()[:1000000])
if os.environ.get("CI"):
    # 共享的 CI 磁盘上，前后空闲空间之差会被别的进程干扰（实测出现过 -1 MB），本机仍严格检查
    print("SKIP 克隆不额外占用空间（CI 共享磁盘，空闲空间测量不稳定）")
else:
    check("克隆不额外占用空间（120MB 文件，占用应远小于 120MB）", 0 <= used < 40, f"实际占用 {used} MB")
check("不带账号数据：second 里没有 config.json", not (ROOT / "second" / "config.json").exists())
# 5 模拟 second 登录后的会话目录
ob = ROOT / "second" / "claude-code-sessions" / "acctB" / "orgB"
wj(ob / "local_s1.json", lastActivityAt=1500, cliSessionId="c1", isArchived=False)     # 比 A 旧
wj(ob / "local_s2.json", lastActivityAt=1800, cliSessionId="c2", isArchived=False)     # 比 A 新
wj(ob / "local_s4.json", lastActivityAt=900, cliSessionId="c4", isArchived=False)      # 仅 B 有
wj(ob / "local_t1.json", lastActivityAt=500, cliSessionId="cB", isArchived=False)      # 与 A 活动时间相同但指针不同 -> 冲突
(ob / "deleted_sX").write_text("deleted-mark")                                          # B 删过 sX
(ob / "archived-sessions.idx").write_text(json.dumps({"v": 1, "archived": []}, separators=(",", ":")))
(ob / "scheduled-tasks.json").write_text("B-tasks")
snap = {p: p.read_bytes() for p in [oa / "local_t1.json", ob / "local_t1.json", oa / "scheduled-tasks.json", ob / "scheduled-tasks.json"]}
# 6 sync 预演
before = {p: p.read_bytes() for d in (oa, ob) for p in d.glob("*") if p.is_file()}
rc, out = run("sync")
after = {p: p.read_bytes() for d in (oa, ob) for p in d.glob("*") if p.is_file()}
check("sync 预演不改动任何文件", before == after and rc == 0, out)
check("预演报告：冲突 1 个", "指针冲突（不动）1" in out, out)
# 7 sync 执行
rc, out = run("sync", "--go")
check("sync --go 成功", rc == 0, out)
check("A 的 s2 被 B 的更新版覆盖", rj(oa / "local_s2.json")["lastActivityAt"] == 1800)
check("B 的 s1 被 A 的更新版覆盖", rj(ob / "local_s1.json")["lastActivityAt"] == 2000)
check("B 的独有 s4 补到 A", (oa / "local_s4.json").exists())
check("A 的 s3 补到 B 且保持已归档", (ob / "local_s3.json").exists() and rj(ob / "local_s3.json")["isArchived"] is True)
check("删除标记生效：sX 没有被复制回 B", not (ob / "local_sX.json").exists())
check("冲突会话两边都没动", (oa / "local_t1.json").read_bytes() == snap[oa / "local_t1.json"] and (ob / "local_t1.json").read_bytes() == snap[ob / "local_t1.json"])
check("scheduled-tasks.json 各自保持原样", (oa / "scheduled-tasks.json").read_text() == "A-tasks" and (ob / "scheduled-tasks.json").read_text() == "B-tasks")
check("B 的归档索引按文件重写为 [s3]", rj(ob / "archived-sessions.idx")["archived"] == ["local_s3"])
check("A 的归档索引保持 [s3]", rj(oa / "archived-sessions.idx")["archived"] == ["local_s3"])
check("含 _backup 的子目录没被当作会话目录", not list((ROOT / "second").glob("**/claude-code-sessions_backup_x")))
bk = ROOT / "_backups"
bk_s2 = list(bk.glob("*/main/claude-code-sessions/acctA/orgA/local_s2.json"))
bk_s1 = list(bk.glob("*/second/claude-code-sessions/acctB/orgB/local_s1.json"))
check("被覆盖的文件已备份，且备份的是覆盖前的旧内容",
      bool(bk_s2) and rj(bk_s2[0])["lastActivityAt"] == 1000 and bool(bk_s1) and rj(bk_s1[0])["lastActivityAt"] == 1500,
      f"s2备份={bk_s2} s1备份={bk_s1}")
# 8 幂等
rc, out = run("sync", "--go")
check("再次 sync 无新增无更新", "新增 0 处、更新 0 处" in out, out)
# 9 use 切换
rc, out = run("use", "second", "--go")
check("use second 成功，链接指向 second", rc == 0 and LIVE.resolve() == (ROOT / "second").resolve(), out)
rc, out = run("use", "main", "--go")
check("use main 切回，main 的登录态仍在", rc == 0 and LIVE.resolve() == (ROOT / "main").resolve() and rj(LIVE / "config.json")["login"] == "A", out)
rc, out = run("use", "nope", "--go")
check("use 不存在的档案被拒绝", rc != 0, out)
# 10 App 运行时拒绝
env2 = dict(ENV, CLAUDE_SWITCH_FAKE_RUNNING="1")
tgt = LIVE.resolve()
rc, out = run("use", "second", "--go", env=env2)
check("App 运行且退不出去时 use 被拒绝，链接不变", rc != 0 and LIVE.resolve() == tgt, out)
rc, out = run("init", "zz", "--go", env=env2)
rc2, out2 = run("add", "third", "--go", env=env2)
check("App 运行时 add 被拒绝", rc2 != 0 and not (ROOT / "third").exists(), out2)
rc3, out3 = run("sync", "--go", env=env2)
check("App 运行时 sync --go 被拒绝", rc3 != 0, out3)
# 11 备份轮转
for i in range(5):
    time.sleep(1.1)
    wj(oa / "local_s1.json", lastActivityAt=5000 + i, cliSessionId="c1", isArchived=False)
    run("sync", "--go")
nb = len(list((ROOT / "_backups").iterdir()))
check("备份轮转：_backups 只保留 3 份", nb == 3, f"实际 {nb}")
check("旧备份进了（沙盒）废纸篓而不是被删除", len(list(TRASH.iterdir())) >= 3, str(list(TRASH.iterdir())))
# 12 uninstall
rc, out = run("uninstall", "--go")
check("uninstall 后 Claude 是真实目录且数据在", rc == 0 and LIVE.is_dir() and not LIVE.is_symlink() and rj(LIVE / "config.json")["login"] == "A", out)
check("uninstall 后其他档案保留", (ROOT / "second").is_dir())
check("uninstall 后不再是已初始化状态", run("use", "second")[0] != 0)

print("\n沙盒目录:", T)
print("全部通过" if not fails else f"失败 {len(fails)} 项: {fails}")
sys.exit(1 if fails else 0)
