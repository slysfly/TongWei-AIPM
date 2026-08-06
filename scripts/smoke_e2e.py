#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务端端到端冒烟测试：验证「后台异步 LLM 任务 + 实时 WebSocket 推送」全链路。
在服务器上以 venv 运行（cd /opt/AI-PM/backend && venv/bin/python smoke_e2e.py）：
  1) 用 create_access_token 为 admin 铸 JWT（免猜密码）
  2) 取/建一个项目
  3) 连接 /api/v1/ws/events/{token}，实时收集 task_progress / task_done
  4) POST /async-tasks 触发 analyze_project + summarize_lessons
  5) 轮询确认两个任务 success + result
  6) 输出 PASS / FAIL 与事件统计
依赖 websockets + httpx；若缺失则自动 pip 安装到当前解释器。
"""
import asyncio
import json
import os
import sys
import subprocess

BACKEND = os.environ.get("AIPM_BACKEND_DIR", os.getcwd())
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def ensure_deps():
    try:
        import websockets  # noqa: F401
        import httpx  # noqa: F401
    except ImportError:
        print("[deps] 安装 websockets / httpx ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "websockets", "httpx"], check=False)


def log(*a):
    print("[smoke]", *a, flush=True)


async def main():
    ensure_deps()

    from app.db.session import async_session_maker
    from app.models import User, Project
    from app.core.security import create_access_token
    from sqlalchemy import select
    import websockets
    import httpx

    # 1) 取 admin（或任意）用户
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.is_superuser.is_(True)))).scalars().first()
        if not user:
            user = (await db.execute(select(User))).scalars().first()
        if not user:
            log("FAIL: 数据库中无任何用户")
            return
        uid = user.id
        proj = (await db.execute(select(Project).where(Project.is_deleted == False))).scalars().first()
        if not proj:
            proj = Project(name="冒烟测试项目", status="planning", methodology="agile")
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
        pid = proj.id
        log(f"user={uid}  project={pid} ({proj.name})")

    token = create_access_token({"sub": str(uid)})
    base = "http://127.0.0.1:8000/api/v1"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    events: list = []
    results: dict = {}
    done_flag = {"all": False}

    async def ws_listen():
        uri = f"ws://127.0.0.1:8000/api/v1/ws/events/{token}"
        try:
            async with websockets.connect(uri, max_size=None) as ws:
                log("WS 已连接")
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2)
                    except asyncio.TimeoutError:
                        if done_flag["all"]:
                            break
                        continue
                    msg = json.loads(raw)
                    events.append(msg)
                    log(f"WS <- type={msg.get('type')} task={msg.get('task_id')} prog={msg.get('progress')} msg={msg.get('message')}")
        except Exception as e:  # noqa: BLE001
            log(f"WS 异常: {e!r}")

    listener = asyncio.create_task(ws_listen())
    await asyncio.sleep(1.5)  # 确保 WS 已连接再触发任务

    # 2) 触发两个异步任务
    async with httpx.AsyncClient(timeout=200) as cli:
        r1 = await cli.post(f"{base}/async-tasks", headers=headers,
                            json={"task_type": "analyze_project", "params": {"project_id": pid}})
        r2 = await cli.post(f"{base}/async-tasks", headers=headers,
                            json={"task_type": "summarize_lessons", "params": {"project_id": pid}})
        t1 = (r1.json().get("data") or {}).get("task_id")
        t2 = (r2.json().get("data") or {}).get("task_id")
        log(f"analyze_project task_id={t1}")
        log(f"summarize_lessons task_id={t2}")
        if not t1 or not t2:
            log(f"FAIL: 创建异步任务未返回 task_id | r1={r1.text} | r2={r2.text}")
            done_flag["all"] = True
            listener.cancel()
            return

    # 3) 轮询等待两个任务完成
    async with httpx.AsyncClient(timeout=200) as cli:
        for tid, name in [(t1, "analyze_project"), (t2, "summarize_lessons")]:
            for _ in range(150):
                rr = await cli.get(f"{base}/async-tasks/{tid}", headers=headers)
                d = (rr.json() or {}).get("data") or {}
                st = d.get("status")
                if st in ("success", "failed"):
                    results[name] = d
                    log(f"POLL {name} => {st}")
                    break
                await asyncio.sleep(2)
            else:
                log(f"TIMEOUT 等待 {name} 完成")

    done_flag["all"] = True
    await asyncio.sleep(1)
    listener.cancel()

    # 4) 校验
    prog_events = [e for e in events if e.get("type") == "task_progress"]
    done_events = [e for e in events if e.get("type") == "task_done"]
    log("===== 结果汇总 =====")
    log(f"WS task_progress 事件数: {len(prog_events)}")
    log(f"WS task_done 事件数: {len(done_events)}")
    log(f"analyze_project 状态: {results.get('analyze_project', {}).get('status')}")
    log(f"summarize_lessons 状态: {results.get('summarize_lessons', {}).get('status')}")
    for name, d in results.items():
        if d.get("status") == "failed":
            log(f"{name} 失败原因: {d.get('error')}")
    sl = results.get("summarize_lessons") or {}
    sl_result = sl.get("result") or {}
    if sl_result:
        log(f"summarize_lessons result.mode: {sl_result.get('mode')}")
        log(f"summarize_lessons result.lessons: {sl_result.get('lessons')}")

    ok = (
        len(prog_events) >= 2
        and len(done_events) >= 2
        and results.get("analyze_project", {}).get("status") == "success"
        and results.get("summarize_lessons", {}).get("status") == "success"
    )
    log(f"RESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
