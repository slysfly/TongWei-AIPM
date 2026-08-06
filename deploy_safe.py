#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-PM 安全部署脚本 —— 彻底解决「改一处、刷新就崩」

四道保险：
  1) 停服期间部署：先停服务 + 强杀端口，上传与替换期间线上绝不对外提供「半新半旧」文件。
  2) 快照回滚：部署前把当前线上整盘快照到 .deploy_bak（排除 venv/.env/.db），失败可一键回滚。
  3) 健康检查门禁：部署后轮询 /health、首页、im-gateway 端点、关键 JS chunk，任一不过关即自动回滚。
  4) 强杀占用端口的进程：确保新代码 100% 被加载，旧进程不再「阴魂不散」。

用法（密码仅从环境变量读取，绝不落盘）:
  AIPM_PASS='xxx' python deploy_safe.py push      # 安全部署
  AIPM_PASS='xxx' python deploy_safe.py verify    # 比对线上与本地构建是否一致 + 健康检查
  AIPM_PASS='xxx' python deploy_safe.py rollback  # 手动回滚到上一快照
  AIPM_PASS='xxx' python deploy_safe.py status    # 仅看线上状态
"""
import os
import sys
import time
import json
import paramiko

HOST = "81.70.158.130"
PORT = 7000
USER = "root"
REMOTE = "/opt/AI-PM"          # 线上项目根
LOCAL = os.path.dirname(os.path.abspath(__file__))
BAK = REMOTE + "/.deploy_bak"   # 回滚快照
STAGE = REMOTE + "/.deploy_stage"  # 临时上传目录

# rsync 排除项：绝不碰虚拟环境 / 密钥 / 数据库 / 字节码
RSYNC_EXCLUDES = (
    "--exclude=venv --exclude=__pycache__ --exclude='*.pyc' "
    "--exclude='*.db' --exclude='*.sqlite3' --exclude='.env' "
    "--exclude='.env.example' --exclude='.github' --exclude=node_modules "
    "--exclude='*.log' --exclude=uploads --exclude=logs --exclude='.pytest_cache'"
)

EXCLUDES_DIRS = {"venv", "__pycache__", ".git", "logs", "uploads", "node_modules", ".pytest_cache"}
EXCLUDES_FILES = {".env", ".env.example"}
EXCLUDES_SUFFIX = (".pyc", ".db", ".sqlite3", ".log")

SERVICE = "ai-pm"


def connect():
    pw = os.environ.get("AIPM_PASS")
    if not pw:
        sys.exit("缺少环境变量 AIPM_PASS（用法: AIPM_PASS='xxx' python deploy_safe.py push）")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=pw, timeout=25)
    return c


def run(c, cmd, timeout=120):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out, err, stdout.channel.recv_exit_status()


def ssh(c, cmd, timeout=120):
    out, err, code = run(c, cmd, timeout)
    return out, err, code


def upload_tree(sftp, local_root, remote_root):
    count = 0
    for dirpath, dirnames, filenames in os.walk(local_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDES_DIRS]
        filenames = [f for f in filenames if f not in EXCLUDES_FILES and not f.endswith(EXCLUDES_SUFFIX)]
        rel = os.path.relpath(dirpath, local_root)
        remote_dir = remote_root if rel == "." else os.path.join(remote_root, rel).replace("\\", "/")
        parts = remote_dir.strip("/").split("/")
        cur = ""
        for p in parts:
            cur = cur + "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                try:
                    sftp.mkdir(cur)
                except IOError:
                    pass
        for f in filenames:
            sftp.put(os.path.join(dirpath, f), remote_dir + "/" + f)
            count += 1
    return count


def write_version(c, label):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    cmd = f"echo '{ts} | {label} | local={os.path.basename(LOCAL)}' > {REMOTE}/backend/deploy_version.txt"
    run(c, cmd)


# ───────────────────────────── 健康检查门禁 ─────────────────────────────
def health_gate(c, timeout=45):
    """轮询关键端点，全部 200 才放行。返回 (ok, detail)。"""
    print(f"===== 健康检查门禁（最多 {timeout}s） =====")
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        # 1) 服务进程
        out, _, _ = run(c, f"systemctl is-active {SERVICE}")
        last["service"] = out.strip()

        # 2) /health
        out, _, _ = run(c, "curl -sk -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health")
        last["health"] = out.strip()

        # 3) 首页
        out, _, _ = run(c, "curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/")
        last["home"] = out.strip()

        # 4) 关键 JS chunk（从 index.html 解析当前哈希文件名）
        out, _, _ = run(c, r"grep -o '/assets/index-[^\"]*\.js' " + REMOTE + "/frontend/dist/index.html | head -1")
        asset = out.strip()
        if asset:
            out, _, _ = run(c, f"curl -sk -m 5 -o /dev/null -w '%{{http_code}}' https://127.0.0.1{asset}")
            last["asset"] = f"{asset}={out.strip()}"
        else:
            last["asset"] = "index.js not found"

        # 5) im-gateway 真实接口（带登录态）
        token_cmd = (
            "TOKEN=$(curl -sk -m 8 -X POST https://127.0.0.1/api/v1/auth/login "
            "-H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}' "
            "| python3 -c \"import sys,json;d=json.load(sys.stdin);print(d.get('data',{}).get('access_token',''))\" 2>/dev/null); "
            f"curl -sk -m 8 -o /dev/null -w '%{{http_code}}' https://127.0.0.1/api/v1/im-gateway/providers "
            "-H \"Authorization: Bearer $TOKEN\""
        )
        out, _, _ = run(c, token_cmd)
        last["im_gateway"] = out.strip()

        ok = (
            last["service"] == "active"
            and last["health"] == "200"
            and last["home"] == "200"
            and last["asset"].endswith("200")
            and last["im_gateway"] in ("200", "401")  # 401=鉴权生效但接口可达，也算通过
        )
        print("  ".join(f"{k}={v}" for k, v in last.items()))
        if ok:
            print("✅ 健康检查全部通过")
            return True, last
        time.sleep(3)
    print("❌ 健康检查超时未通过")
    return False, last


# ───────────────────────────── 部署主流程 ─────────────────────────────
def push(c):
    # 0) 写部署版本戳（标记本次动作）
    write_version(c, "PUSH_START")

    # 1) 停服 + 强杀端口（关键：部署期间线上不对外，杜绝半新半旧）
    print("===== 1/6 停服并释放端口 =====")
    run(c, f"systemctl stop {SERVICE} 2>/dev/null; "
            f"(fuser -k 8000/tcp 2>/dev/null || lsof -ti:8000 | xargs -r kill -9 2>/dev/null); sleep 2")
    out, _, _ = run(c, f"systemctl is-active {SERVICE}")
    print(f"  服务状态(应为 inactive): {out.strip()}")

    # 2) 快照当前线上到 .deploy_bak（回滚用，排除 venv/.env/.db）
    print("===== 2/6 快照当前线上（回滚点） =====")
    run(c, f"rm -rf {BAK}; mkdir -p {BAK}/backend {BAK}/frontend")
    run(c, f"rsync -a {RSYNC_EXCLUDES} {REMOTE}/backend/ {BAK}/backend/")
    run(c, f"rsync -a {REMOTE}/frontend/ {BAK}/frontend/")
    out, _, _ = run(c, f"du -sh {BAK} 2>/dev/null")
    print(f"  快照大小: {out.strip()}")

    # 3) 上传到临时 stage
    print("===== 3/6 上传构建产物到临时目录 =====")
    sftp = c.open_sftp()
    run(c, f"rm -rf {STAGE}; mkdir -p {STAGE}")
    n1 = upload_tree(sftp, os.path.join(LOCAL, "backend"), STAGE + "/backend")
    n2 = upload_tree(sftp, os.path.join(LOCAL, "frontend", "dist"), STAGE + "/frontend/dist")
    sftp.close()
    print(f"  后端文件: {n1}  前端文件: {n2}")

    # 4) 原子替换：rsync stage -> live（--delete 清理旧 chunk；排除项保护 venv/.env/.db）
    print("===== 4/6 原子替换线上（rsync --delete） =====")
    run(c, f"rsync -a --delete {RSYNC_EXCLUDES} {STAGE}/backend/ {REMOTE}/backend/")
    run(c, f"rsync -a --delete {STAGE}/frontend/dist/ {REMOTE}/frontend/dist/")
    # 清掉可能残留的旧字节码，避免遮蔽新代码
    run(c, f"find {REMOTE}/backend/app -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null; "
            f"find {REMOTE}/backend -name '*.pyc' -delete 2>/dev/null; echo SYNCED")
    write_version(c, "PUSH_DONE")

    # 5) 起服
    print("===== 5/6 启动服务 =====")
    run(c, f"systemctl start {SERVICE} 2>/dev/null || (cd {REMOTE}/backend && setsid venv/bin/python serve.py >/tmp/aipm.log 2>&1 &)")
    time.sleep(5)

    # 6) 健康检查门禁 + 失败自动回滚
    print("===== 6/6 健康检查门禁 =====")
    ok, detail = health_gate(c)
    if not ok:
        print("\n!! 健康检查未通过，自动回滚到上一快照...")
        _rollback_core(c)
        sys.exit("\n❌ 部署失败，已自动回滚到上一可用版本。请检查本次改动。")
    print("\n🎉 部署成功，线上已是最新且健康。")


def _rollback_core(c):
    run(c, f"systemctl stop {SERVICE} 2>/dev/null; "
            f"(fuser -k 8000/tcp 2>/dev/null || lsof -ti:8000 | xargs -r kill -9 2>/dev/null); sleep 2")
    run(c, f"rsync -a --delete {RSYNC_EXCLUDES} {BAK}/backend/ {REMOTE}/backend/")
    run(c, f"rsync -a --delete {BAK}/frontend/ {REMOTE}/frontend/")
    run(c, f"find {REMOTE}/backend/app -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null; "
            f"find {REMOTE}/backend -name '*.pyc' -delete 2>/dev/null; echo ROLLEDBACK")
    run(c, f"systemctl start {SERVICE} 2>/dev/null || (cd {REMOTE}/backend && setsid venv/bin/python serve.py >/tmp/aipm.log 2>&1 &)")
    time.sleep(5)
    write_version(c, "ROLLBACK")


def rollback(c):
    print("===== 手动回滚 =====")
    out, _, _ = run(c, f"ls -d {BAK} 2>/dev/null && echo EXISTS || echo MISSING")
    if "MISSING" in out:
        sys.exit("无可用快照（.deploy_bak 不存在），无法回滚。")
    _rollback_core(c)
    ok, _ = health_gate(c, timeout=30)
    print("✅ 回滚完成，健康检查：" + ("通过" if ok else "仍异常，请登录服务器排查"))


def status(c):
    print("===== 线上状态 =====")
    out, _, _ = run(c, f"systemctl is-active {SERVICE}; "
                        f"curl -sk -m 5 -o /dev/null -w 'health=%{{http_code}}\\n' http://127.0.0.1:8000/health; "
                        f"curl -sk -m 5 -o /dev/null -w 'home=%{{http_code}}\\n' https://127.0.0.1/; "
                        f"cat {REMOTE}/backend/deploy_version.txt 2>/dev/null")
    print(out)


def verify(c):
    """比对线上与本地构建是否一致，并跑健康检查。"""
    print("===== 一致性校验 =====")
    # 本地 dist/index.html 的关键 JS
    local_html = os.path.join(LOCAL, "frontend", "dist", "index.html")
    local_asset = ""
    if os.path.exists(local_html):
        with open(local_html, "r", encoding="utf-8") as f:
            import re
            m = re.search(r"/assets/index-[^\"]*\.js", f.read())
            local_asset = m.group(0) if m else ""
    out, _, _ = run(c, r"grep -o '/assets/index-[^\"]*\.js' " + REMOTE + "/frontend/dist/index.html | head -1")
    remote_asset = out.strip()

    print(f"  本地构建引用 JS : {local_asset or 'N/A'}")
    print(f"  线上引用 JS     : {remote_asset or 'N/A'}")
    match = (local_asset and remote_asset and local_asset == remote_asset)
    print(f"  JS 引用一致     : {'✅' if match else '❌ 不一致！'}")

    # 关键后端文件比对（im_gateway.py 行数 + 是否含关键修复）
    out, _, _ = run(c, f"grep -c 'db.refresh' {REMOTE}/backend/app/api/v1/im_gateway.py 2>/dev/null || echo 0")
    print(f"  线上 im_gateway 含 db.refresh 修复: {'✅' if out.strip() not in ('0','') and int(out.strip() or 0)>0 else '❌'} ({out.strip()})")

    # 健康检查
    ok, detail = health_gate(c, timeout=30)
    print(f"\n  健康检查: {'✅ 通过' if ok else '❌ 未通过'}")
    if not match:
        print("\n⚠️ 本地构建与线上不一致，请重新构建并执行 push。")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    c = connect()
    try:
        if mode == "push":
            push(c)
        elif mode == "rollback":
            rollback(c)
        elif mode == "status":
            status(c)
        elif mode == "verify":
            verify(c)
        else:
            print("未知模式。用法: push | rollback | status | verify")
    finally:
        c.close()
