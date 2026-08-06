#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地编排：通过 paramiko 把 scripts/smoke_e2e.py 上传到服务器并以 venv 运行，
捕获输出并打印 PASS/FAIL。用于「带鉴权的真实端到端」验证（免猜密码，用铸 token）。
用法：AIPM_PASS='xxx' python run_smoke.py
"""
import os
import sys
import paramiko

HOST = "81.70.158.130"
PORT = 7000
USER = "root"
REMOTE_DIR = "/opt/AI-PM"
LOCAL = os.path.dirname(os.path.abspath(__file__))
REMOTE_SCRIPT = "/tmp/aipm_smoke_e2e.py"


def connect():
    pw = os.environ.get("AIPM_PASS")
    if not pw:
        sys.exit("缺少环境变量 AIPM_PASS")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=pw, timeout=25)
    return c


def run(c, cmd):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=900)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out, err, stdout.channel.recv_exit_status()


def main():
    print("===== 上传冒烟脚本 =====")
    c = connect()
    sftp = c.open_sftp()
    sftp.put(os.path.join(LOCAL, "scripts", "smoke_e2e.py"), REMOTE_SCRIPT)
    sftp.close()
    print(f"  已上传 {REMOTE_SCRIPT}")

    print("===== 远端执行（cd {}/backend && venv/bin/python {}）=====".format(REMOTE_DIR, REMOTE_SCRIPT))
    out, err, code = run(
        c,
        f"cd {REMOTE_DIR}/backend && venv/bin/python {REMOTE_SCRIPT}",
    )
    print(out)
    if err.strip():
        print("STDERR:", err)
    print(f"退出码: {code}")
    c.close()
    if code == 0:
        print("\n✅ 端到端冒烟：PASS")
    else:
        print("\n❌ 端到端冒烟：FAIL（见上方输出）")
    sys.exit(code)


if __name__ == "__main__":
    main()
