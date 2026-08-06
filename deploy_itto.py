#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ITTO 物料驱动管线 · 精准部署脚本（仅上传本次变更文件，避免覆盖线上独有的 RAG/kb_id 等生产文件）
- 后端：仅 4 个本次修改/新增文件（agent.py / agent_registry.py / pmbok_agents.py / agent_materials.py）
- 前端：整体替换 dist（clean build 已清空旧 chunk）+ 同步 src + public 源码
- 完成后清理远端 __pycache__、重启 ai-pm、自检端点
密码从环境变量 AIPM_PASS 读取（不在文件/命令行明文）。
"""
import os
import sys
import time
import paramiko

HOST = "81.70.158.130"
PORT = 7000
USER = "root"
REMOTE = "/opt/AI-PM"
LOCAL = os.path.dirname(os.path.abspath(__file__))

# 认证方式：默认走 ~/.ssh/aipm_deploy 公钥；如需密码可设 AIPM_USE_PASS=1 并提供 AIPM_PASS
KEY_PATH = os.path.expanduser(os.environ.get("AIPM_KEY", "~/.ssh/aipm_deploy"))

# 仅本次变更的后端文件（相对 backend/ 的路径）
BACKEND_FILES = [
    "app/api/v1/ai_routes/agent.py",
    "app/services/ai/agent_registry.py",
    "app/services/ai/pmbok_agents.py",
    "app/services/ai/agent_materials.py",
]


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if os.environ.get("AIPM_USE_PASS") == "1":
        pw = os.environ.get("AIPM_PASS")
        if not pw:
            sys.exit("AIPM_USE_PASS=1 但缺少 AIPM_PASS")
        c.connect(HOST, port=PORT, username=USER, password=pw, timeout=25)
    else:
        if not os.path.exists(KEY_PATH):
            sys.exit(f"找不到私钥 {KEY_PATH}；若要用密码，请设置 AIPM_USE_PASS=1 + AIPM_PASS")
        pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
        c.connect(HOST, port=PORT, username=USER, pkey=pkey, timeout=25)
    return c


def run(c, cmd):
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out, err, stdout.channel.recv_exit_status()


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


def upload_file(sftp, local_file, remote_file):
    mkdir_p(sftp, os.path.dirname(remote_file))
    sftp.put(local_file, remote_file)


def upload_tree(sftp, local_root, remote_root, excludes_dirs=None, excludes_suffix=None):
    excludes_dirs = excludes_dirs or {"node_modules", "__pycache__", ".git"}
    excludes_suffix = excludes_suffix or (".pyc",)
    count = 0
    for dirpath, dirnames, filenames in os.walk(local_root):
        dirnames[:] = [d for d in dirnames if d not in excludes_dirs]
        rel = os.path.relpath(dirpath, local_root)
        remote_dir = remote_root if rel == "." else os.path.join(remote_root, rel).replace("\\", "/")
        mkdir_p(sftp, remote_dir)
        for f in filenames:
            if any(f.endswith(s) for s in excludes_suffix):
                continue
            sftp.put(os.path.join(dirpath, f), remote_dir + "/" + f)
            count += 1
    return count


def main():
    c = connect()
    try:
        sftp = c.open_sftp()
        print("===== 上传后端（仅本次变更 4 文件） =====")
        for rel in BACKEND_FILES:
            local = os.path.join(LOCAL, "backend", rel)
            remote = REMOTE + "/backend/" + rel
            if not os.path.exists(local):
                print(f"  !! 本地缺失 {rel}，跳过")
                continue
            upload_file(sftp, local, remote)
            print(f"  ✓ {rel}")
        sftp.close()

        print("===== 清理远端 __pycache__ =====")
        run(c, f"find {REMOTE}/backend/app -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null; "
                f"find {REMOTE}/backend -name '*.pyc' -delete 2>/dev/null; echo CLEANED")

        print("===== 上传前端 dist（整体替换，避免旧 chunk 残留） =====")
        run(c, f"rm -rf {REMOTE}/frontend/dist")
        sftp = c.open_sftp()
        n1 = upload_tree(sftp, os.path.join(LOCAL, "frontend", "dist"), REMOTE + "/frontend/dist")
        print(f"  dist 文件数: {n1}")
        print("===== 同步前端 src（仅 ITTO 相关文件，避免回退其他页面） =====")
        SRC_FILES = [
            "src/pages/PmbokAgents.tsx",
            "src/api/index.ts",
            "src/components/AgentRunDialog.tsx",
            "src/utils/markdown.ts",
        ]
        for rel in SRC_FILES:
            upload_file(sftp, os.path.join(LOCAL, "frontend", rel), REMOTE + "/frontend/" + rel)
            print(f"  ✓ src/{rel}")
        n2 = len(SRC_FILES)
        print(f"  src 文件数: {n2}")
        print("===== 同步前端 public（含 sw.js v6） =====")
        n3 = upload_tree(sftp, os.path.join(LOCAL, "frontend", "public"), REMOTE + "/frontend/public")
        print(f"  public 文件数: {n3}")
        sftp.close()

        print("===== 后端导入冒烟（确认 4 文件可正常 import） =====")
        smoke = (
            f"cd {REMOTE}/backend && venv/bin/python -c \"import app.api.v1.ai_routes.agent as a, "
            f"app.services.ai.agent_registry as r, app.services.ai.pmbok_agents as p, "
            f"app.services.ai.agent_materials as m; print('IMPORT_OK', r.get_structured_itto('report')['inputs'][:1])\""
        )
        out, err, code = run(c, smoke)
        print(out)
        if err.strip():
            print("SMOKE_ERR:", err[:500])

        print("===== 重启服务 =====")
        out, _, _ = run(c, "systemctl list-unit-files 2>/dev/null | grep -iE 'ai-pm|aipm'")
        svc = None
        for line in out.splitlines():
            if "ai-pm.service" in line:
                svc = "ai-pm"; break
        if svc:
            run(c, f"systemctl restart {svc}")
            time.sleep(9)
            out, _, _ = run(c, f"systemctl is-active {svc}")
            print(f"  服务 {svc} 状态: {out.strip()}")
        else:
            print("  未找到 systemd 服务")

        print("===== 部署后自检 =====")
        out, _, _ = run(c,
            "curl -sk -m 8 -o /dev/null -w 'HTTPS_/=%{http_code}\\n' https://127.0.0.1/ ; "
            "curl -sk -m 8 -o /dev/null -w 'agents=%{http_code}\\n' https://127.0.0.1/api/v1/agents ; "
            "curl -sk -m 8 -o /dev/null -w 'pmbok-catalog=%{http_code}\\n' https://127.0.0.1/api/v1/agents/pmbok-catalog ; "
            "curl -sk -m 10 -o /dev/null -w 'prepare=%{http_code}\\n' -X POST https://127.0.0.1/api/v1/agents/4.1/prepare -H 'Content-Type: application/json' -d '{\"project_id\":null}'"
        )
        print(out)
    finally:
        c.close()


if __name__ == "__main__":
    main()
