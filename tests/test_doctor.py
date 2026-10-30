#!/usr/bin/env python3
"""doctor 沙盒测试：构造「同一会话出现在两个转录文件夹」的各种情形，确认只读、判断正确。"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "claude-switch"
T = Path(tempfile.mkdtemp(prefix="doc."))
ASUP, PROJ = T / "asup", T / "projects"
ENV = dict(os.environ, CLAUDE_SWITCH_ASUP=str(ASUP), CLAUDE_SWITCH_TRASH=str(T / "trash"),
           CLAUDE_SWITCH_TEST="1", CLAUDE_SWITCH_PROJECTS=str(PROJ))
fails = []


def run(*a):
    r = subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout + r.stderr


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if not cond and extra else ""))
    if not cond:
        fails.append(name)


(ASUP / "Claude").mkdir(parents=True)
rc, _ = run("init", "main", "--go")
org = ASUP / "Claude-Profiles" / "main" / "claude-code-sessions" / "acct" / "org"
org.mkdir(parents=True)
(org / "local_a.json").write_text(json.dumps({"cliSessionId": "sidprefix", "title": "前缀情形", "lastActivityAt": 1}))
(org / "local_b.json").write_text(json.dumps({"cliSessionId": "sidconflict", "title": "冲突情形", "lastActivityAt": 1}))
for d in ("L", "P"):
    (PROJ / d).mkdir(parents=True)
(PROJ / "L" / "sidprefix.jsonl").write_text("line1\nline2\n")
(PROJ / "P" / "sidprefix.jsonl").write_text("line1\nline2\nline3\n")
(PROJ / "L" / "sidconflict.jsonl").write_text("AAAA\n")
(PROJ / "P" / "sidconflict.jsonl").write_text("BBBBBB\n")
(PROJ / "L" / "same.jsonl").write_text("x\n")
(PROJ / "P" / "same.jsonl").write_text("x\n")
before = sorted((p.name, p.stat().st_size) for p in PROJ.rglob("*.jsonl"))

rc, out = run("doctor")
check("doctor 正常退出", rc == 0, out)
check("前缀情形：标明较大的那份是完整的", "前缀情形" in out and "较大的那份是完整的" in out, out)
check("冲突情形：提示需要人工合并", "冲突情形" in out and "人工合并" in out, out)
check("完全相同的不报告", "same" not in out, out)
check("统计 2 个分裂", "共 2 个会话有分裂" in out, out)
after = sorted((p.name, p.stat().st_size) for p in PROJ.rglob("*.jsonl"))
check("doctor 只读：文件未变", before == after)
import shutil
shutil.rmtree(T)
print("全部通过" if not fails else f"失败 {len(fails)} 项")
sys.exit(1 if fails else 0)
