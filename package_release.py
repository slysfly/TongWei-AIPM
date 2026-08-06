#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通维AI 安装包发布脚本（安全打包，密钥绝不随包走）

用法：
    python package_release.py                 # 打包到 ./dist/通维AI-<version>
    python package_release.py --dest D:\\pkg  # 指定输出目录

行为：
    - 复制后端 backend/ 与前端 frontend/（含已构建的 frontend/dist）到发布目录；
    - 强制排除：.env / .env.*、venv、__pycache__、*.db、*.log、node_modules、
      QA 冒烟脚本（tests/、scripts/smoke_run.py、_verify*.py）、.pytest_cache 等；
    - 仅复制，绝不删除源文件；输出发布清单到 dist/ 根。

注意：发布前请确认 backend/.env 未被复制（脚本已强制排除）。
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# 后端/前端子目录名
BACKEND = "backend"
FRONTEND = "frontend"

# 全局排除（相对路径片段命中即跳过）
# 注意：刻意【不】排除 dist —— 我们需要随包发布已构建的 frontend/dist，
# 这样全新 Linux 离线也能直接部署前端（无需 node/npm/联网构建）。
EXCLUDE_DIRS = {
    ".git", ".idea", ".vscode",
    "venv", ".venv", "env", "__pycache__",
    "node_modules", ".pytest_cache", ".mypy_cache",
    "build", "release", "output",
    "qa-shots", "dist2",
}
EXCLUDE_FILES_EXACT = {
    ".env", ".env.example.bak",
}
# 通配/后缀排除
EXCLUDE_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".log", ".pyc")
EXCLUDE_NAME_GLOBS = ("_verify", "test_smoke", "smoke_run", "pip_", "pytest_",
                      "vite.config.ts.timestamp", "build2_out", "deploy_pwa_out", "deploy2_out", "_fe_dist")


def _is_excluded(src_rel: str, name: str) -> bool:
    if name in EXCLUDE_DIRS:
        return True
    if name in EXCLUDE_FILES_EXACT:
        return True
    if name.endswith(EXCLUDE_SUFFIXES):
        return True
    # 排除任何名为 .env.xxx 的密钥文件（.env.example 也排除，发布用模板单独处理）
    if name.startswith(".env") and name != ".env.example":
        return True
    if any(name.startswith(g) or name.startswith(g) for g in EXCLUDE_NAME_GLOBS):
        return True
    # 排除 QA 冒烟脚本目录
    if "tests" in src_rel.split(os.sep) or src_rel.endswith("scripts/smoke_run.py"):
        return True
    return False


def _copytree(src: str, dst: str, prefix: str = ""):
    count = 0
    for root, dirs, files in os.walk(src):
        # 原地修剪排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        # 跳过 backend/ 内陈旧的预构建前端（根 frontend/dist 才是权威，避免重复打包旧产物）
        if prefix == BACKEND:
            dirs[:] = [d for d in dirs if d != "frontend"]
        rel_root = os.path.relpath(root, src)
        for f in files:
            rel = os.path.join(rel_root, f) if rel_root != "." else f
            if _is_excluded(rel, f):
                continue
            s = os.path.join(root, f)
            d = os.path.join(dst, prefix, rel) if prefix else os.path.join(dst, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description="通维AI 安全发布打包（排除密钥/虚拟环境/测试产物）")
    ap.add_argument("--dest", default=None, help="输出根目录（默认 ./dist）")
    ap.add_argument("--version", default=None, help="版本号（默认读 backend/.env.example 的 VERSION）")
    args = ap.parse_args()

    backend_src = os.path.join(ROOT, BACKEND)
    frontend_src = os.path.join(ROOT, FRONTEND)
    if not os.path.isdir(backend_src):
        print(f"[ERROR] 未找到 backend 目录: {backend_src}", file=sys.stderr)
        sys.exit(1)

    # 解析版本
    version = args.version
    if not version:
        ver_file = os.path.join(backend_src, ".env.example")
        if os.path.isfile(ver_file):
            for line in open(ver_file, encoding="utf-8"):
                if line.startswith("VERSION="):
                    version = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    break
    version = version or "unknown"

    dest_root = args.dest or os.path.join(ROOT, "dist")
    out_dir = os.path.join(dest_root, f"通维AI-{version}")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    print(f"[INFO] 打包到: {out_dir}")
    n_b = _copytree(backend_src, out_dir, prefix=BACKEND)
    print(f"[INFO] backend 已复制 {n_b} 个文件")

    if os.path.isdir(frontend_src):
        n_f = _copytree(frontend_src, out_dir, prefix=FRONTEND)
        print(f"[INFO] frontend 已复制 {n_f} 个文件")
    else:
        print("[WARN] 未找到 frontend 目录，跳过")

    # 单独放入干净模板（不含真实密钥）
    example_src = os.path.join(backend_src, ".env.example")
    if os.path.isfile(example_src):
        shutil.copy2(example_src, os.path.join(out_dir, BACKEND, ".env.example"))
        print("[INFO] 已放入 .env.example 模板（不含真实密钥）")

    # 根目录安装器与文档随包发布（全新 Linux 一键部署所需）
    ROOT_INCLUDE = [
        "install.sh", "uninstall.sh", "README-安装包.md", "ai-pm.service",
    ]
    # 额外纳入根目录说明文档（存在才复制）
    for md in os.listdir(ROOT):
        if md.lower().endswith(".md") and md not in ("README-安装包.md",):
            ROOT_INCLUDE.append(md)
    for name in ROOT_INCLUDE:
        src = os.path.join(ROOT, name)
        if os.path.exists(src):
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(out_dir, name))
            else:
                shutil.copy2(src, os.path.join(out_dir, name))
            # 安装脚本保持可执行
            if name.endswith(".sh"):
                try:
                    os.chmod(os.path.join(out_dir, name), 0o755)
                except OSError:
                    pass
            print(f"[INFO] 已纳入根目录文件: {name}")

    # 发布清单
    manifest = os.path.join(out_dir, "RELEASE_MANIFEST.txt")
    with open(manifest, "w", encoding="utf-8") as mf:
        mf.write(f"通维AI 发布包\n版本: {version}\n")
        mf.write("后端: backend/\n前端: frontend/（含已构建 dist，离线可用）\n")
        mf.write("安装器: install.sh / uninstall.sh / ai-pm.service / README-安装包.md\n")
        mf.write("安全说明: 本包不含 .env / 真实密钥；部署时请复制 backend/.env.example 为 backend/.env 并填写实际值。\n")
        mf.write("部署: 解压后执行 `bash install.sh` 即可（需 Python 3.11+，默认 SQLite 零外部依赖）。\n")
    print(f"[OK] 发布包就绪: {out_dir}")
    print("[OK] 已确认排除: .env / venv / *.db / node_modules / QA 冒烟脚本")

    # 打包为 tar.gz 便于传输（排除 .env 等已在前序步骤处理）
    import tarfile
    tgz_path = os.path.join(dest_root, f"通维AI-{version}.tar.gz")
    if os.path.exists(tgz_path):
        os.remove(tgz_path)
    with tarfile.open(tgz_path, "w:gz") as tar:
        tar.add(out_dir, arcname=os.path.basename(out_dir))
    print(f"[OK] 已生成压缩包: {tgz_path}")


if __name__ == "__main__":
    main()
