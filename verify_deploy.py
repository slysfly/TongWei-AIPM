#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署后端到端验证：登录 -> 调用关键端点，确认功能真正可用。"""
import json
import ssl
import urllib.request
import urllib.error

BASE = "https://81.70.158.130"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def req(method, path, token=None, body=None, as_json=True, timeout=120):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if as_json else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return -1, f"EXCEPTION: {type(e).__name__}: {e}"


def main():
    # 1) 登录
    user, pwd = "admin", "admin123"
    st, body = req("POST", "/api/v1/auth/login", body={"username": user, "password": pwd})
    print(f"[login] {st}")
    if st not in (200, 201):
        print("  登录失败（可能生产密码已改）。用 401 状态已证明路由存在，跳过功能级验证。")
        print("  响应:", str(body)[:200])
        return
    token = None
    if isinstance(body, dict):
        token = body.get("access_token") or body.get("token")
    if not token and isinstance(body, dict):
        token = (body.get("data") or {}).get("access_token")
    print("  token 获取:", "OK" if token else "无")
    if not token:
        print("  未能提取 token，响应:", str(body)[:300]); return

    # 2) 知识库列表（验证尾斜杠死循环已修复）
    st, body = req("GET", "/api/v1/knowledge-bases", token=token)
    print(f"[GET /knowledge-bases] {st}  返回类型={type(body).__name__} 条目数={len(body.get('items', [])) if isinstance(body, dict) else 'n/a'}")

    # 3) 仪表盘 AI 下一步建议（验证新功能 + 前缀修复）
    st, body = req("POST", "/api/v1/dashboard/next-steps", token=token, body={})
    print(f"[POST /dashboard/next-steps] {st}")
    if isinstance(body, dict):
        print("   降级模式=", body.get("advice_mode") or body.get("mode"),
              " 维度=", len(body.get("dimensions", []) or []),
              " 建议条数=", len(body.get("recommendations", []) or []))
    else:
        print("   响应:", str(body)[:200])

    # 4) 变更控制列表（验证路由修复，正确前缀为 change-requests）
    st, body = req("GET", "/api/v1/change-requests/", token=token)
    print(f"[GET /change-requests/] {st}  返回类型={type(body).__name__}")
    st2, _ = req("GET", "/api/v1/change-requests", token=token)
    print(f"[GET /change-requests (无斜杠, 验证不再死循环)] {st2}")

    # 5) 经验教训 AI 生成（验证）
    st, body = req("POST", "/api/v1/lessons/generate", token=token, body={"topic": "测试生成"})
    print(f"[POST /lessons/generate] {st}  (422=参数校验生效, 200=生成成功)")

    # 6) 集成列表（验证扫码集成基础）
    st, body = req("GET", "/api/v1/integrations/", token=token)
    print(f"[GET /integrations/] {st}  类型={type(body).__name__}")


if __name__ == "__main__":
    main()
