#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-PM 部署脚本（paramiko 密码登录版）
用法:
  AIPM_PASS='xxx' python deploy_paramiko.py explore   # 仅探查远端结构/服务
  AIPM_PASS='xxx' python deploy_paramiko.py push       # 上传+重启+自检
密码从环境变量 AIPM_PASS 读取，绝不写入文件。
"""
import os
import sys
import paramiko

HOST = "81.70.158.130"
PORT = 7000
USER = "root"
REMOTE_DIR = "/opt/AI-PM"   # 远端项目根（已核实：进程为 /opt/AI-PM/backend/serve.py）
LOCAL = os.path.dirname(os.path.abspath(__file__))

EXCLUDES_DIRS = {"venv", "__pycache__", ".git", "logs", "uploads", "node_modules", ".pytest_cache"}
EXCLUDES_FILES = {".env", ".env.example"}
EXCLUDES_SUFFIX = (".pyc", ".db", ".sqlite3", ".log")


def connect():
    pw = os.environ.get("AIPM_PASS")
    if not pw:
        sys.exit("缺少环境变量 AIPM_PASS")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=pw, timeout=25)
    return c


def run(c, cmd):
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out, err, stdout.channel.recv_exit_status()


def explore(c):
    print("===== 远端探查 =====")
    out, err, _ = run(c, f"ls -la {REMOTE_DIR} 2>/dev/null && echo '---backend/app---' && ls {REMOTE_DIR}/backend/app 2>/dev/null | head && echo '---frontend/dist---' && ls {REMOTE_DIR}/frontend/dist 2>/dev/null | head")
    print(out)
    if err.strip():
        print("ERR:", err)
    out, _, _ = run(c, "systemctl list-unit-files 2>/dev/null | grep -iE 'ai-pm|aipm' || echo 'NO_SYSTEMD_SERVICE'")
    print("--- systemd 服务 ---\n" + out)
    out, _, _ = run(c, "ps aux | grep -E 'serve.py|uvicorn|gunicorn' | grep -v grep || echo 'NO_APP_PROC'")
    print("--- 运行中的进程 ---\n" + out)
    out, _, _ = run(c, "curl -sk -m 6 -o /dev/null -w 'HTTPS_/=%{http_code}\\n' https://127.0.0.1/ ; curl -sk -m 6 -o /dev/null -w 'HTTP_/health=%{http_code}\\n' http://127.0.0.1:8000/health")
    print("--- 当前健康检查 ---\n" + out)


def mkdir_p(sftp, remote_dir):
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


def upload_tree(sftp, local_root, remote_root):
    count = 0
    for dirpath, dirnames, filenames in os.walk(local_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDES_DIRS]
        filenames = [f for f in filenames if f not in EXCLUDES_FILES and not f.endswith(EXCLUDES_SUFFIX)]
        rel = os.path.relpath(dirpath, local_root)
        remote_dir = remote_root if rel == "." else os.path.join(remote_root, rel).replace("\\", "/")
        mkdir_p(sftp, remote_dir)
        for f in filenames:
            local_file = os.path.join(dirpath, f)
            remote_file = remote_dir + "/" + f
            sftp.put(local_file, remote_file)
            count += 1
    return count


def create_tables(c):
    """
    在远端用应用自身的异步引擎执行 Base.metadata.create_all(checkfirst=True)，
    仅创建缺失的表（不会改动/删除已有表与数据）。
    用于新增模型（如 knowledge_base_shares / user_groups / user_group_members）
    在 Alembic 未覆盖时补齐表结构，零数据风险。
    """
    print("===== 远端补齐缺失表（create_all checkfirst） =====")
    script = (
        "cd " + REMOTE_DIR + "/backend && venv/bin/python - <<'PYEOF'\n"
        "import asyncio, sys\n"
        "try:\n"
        "    from app.db.session import Base, engine\n"
        "    import app.models  # 确保全部模型注册到 Base.metadata\n"
        "    async def m():\n"
        "        async with engine.begin() as conn:\n"
        "            await conn.run_sync(Base.metadata.create_all)\n"
        "    asyncio.run(m())\n"
        "    from app.core.migrate import _ensure_offline_columns\n"
        "    asyncio.run(_ensure_offline_columns())\n"
        "    print('CREATE_MISSING_TABLES_OK')\n"
        "except Exception as e:\n"
        "    print('CREATE_TABLES_ERR:', repr(e)); sys.exit(1)\n"
        "PYEOF\n"
    )
    out, err, code = run(c, script)
    print(out)
    if err.strip():
        print("ERR:", err)
    if code != 0:
        print("!! 建表步骤返回非零状态，请排查（不影响已部署代码）")
    return code


def push(c):
    sftp = c.open_sftp()
    print("===== 上传后端源码 backend/app =====")
    n1 = upload_tree(sftp, os.path.join(LOCAL, "backend", "app"), REMOTE_DIR + "/backend/app")
    print(f"  上传文件数: {n1}")
    print("===== 上传后端入口 backend/serve.py =====")
    # serve.py 在 backend 根目录，需单独上传（含静态资源路由等关键修复）
    sftp.put(os.path.join(LOCAL, "backend", "serve.py"), REMOTE_DIR + "/backend/serve.py")
    print("  serve.py 已上传")
    print("===== 上传前端产物 frontend/dist =====")
    n2 = upload_tree(sftp, os.path.join(LOCAL, "frontend", "dist"), REMOTE_DIR + "/frontend/dist")
    print(f"  上传文件数: {n2}")
    print("===== 上传前端源码 frontend/src（与本地源码保持一致，避免将来重建冲掉修复） =====")
    n3 = upload_tree(sftp, os.path.join(LOCAL, "frontend", "src"), REMOTE_DIR + "/frontend/src")
    print(f"  上传文件数: {n3}")
    sftp.close()

    # 清理远端陈旧字节码，避免旧 .pyc 遮蔽新代码
    print("===== 清理远端 __pycache__ =====")
    run(c, "find " + REMOTE_DIR + "/backend/app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; "
            "find " + REMOTE_DIR + "/backend -name '*.pyc' -delete 2>/dev/null; echo CLEANED")

    print("===== 重启服务 =====")
    out, _, _ = run(c, "systemctl list-unit-files 2>/dev/null | grep -iE 'ai-pm|aipm'")
    svc = None
    for line in out.splitlines():
        if "ai-pm.service" in line:
            svc = "ai-pm"; break
        if "aipm.service" in line:
            svc = "aipm"; break
    if svc:
        run(c, f"systemctl restart {svc}")
        import time; time.sleep(8)
        out, _, _ = run(c, f"systemctl is-active {svc}")
        print(f"  服务 {svc} 状态: {out.strip()}")
    else:
        print("  未找到 systemd 服务，尝试 pkill + 重启 uvicorn")
        run(c, "pkill -f serve.py; sleep 2; cd " + REMOTE_DIR + "/backend && (setsid venv/bin/python serve.py >/tmp/aipm.log 2>&1 &)")
        import time; time.sleep(5)

    print("===== 部署后自检 =====")
    out, _, _ = run(c, "curl -sk -m 8 -o /dev/null -w 'HTTPS_/=%{http_code}\\n' https://127.0.0.1/ ; "
                       "curl -sk -m 8 -o /dev/null -w 'KB_no_loop=%{http_code}\\n' https://127.0.0.1/api/v1/knowledge-bases ; "
                       "curl -sk -m 8 -o /dev/null -w 'next-steps=%{http_code}\\n' -X POST https://127.0.0.1/api/v1/dashboard/next-steps -H 'Content-Type: application/json' -d '{}' ; "
                       "curl -sk -m 8 -o /dev/null -w 'health=%{http_code}\\n' http://127.0.0.1:8000/health")
    print(out)

    # 补齐可能缺失的新表（如分享/用户组相关表），零数据风险
    create_tables(c)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "explore"
    c = connect()
    try:
        if mode == "explore":
            explore(c)
        elif mode == "push":
            push(c)
        elif mode == "tables":
            create_tables(c)
        else:
            print("未知模式，使用 explore / push / tables")
    finally:
        c.close()
