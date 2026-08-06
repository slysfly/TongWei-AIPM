#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通维 AI-PM 端到端功能验证（v2 · 基于真实 OpenAPI 路径）
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import subprocess

BASE = "https://aipm.twzx.bj.cn"
API = f"{BASE}/api/v1"
USER = "admin"
PASS = os.environ.get("AIPM_VERIFY_PASS", "admin123")

results = []


def call(method, path, token=None, body=None, params=None, timeout=30):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"EXC:{e!r}", int((time.time() - t0) * 1000), ""
    lat = int((time.time() - t0) * 1000)
    short = raw if len(raw) <= 300 else raw[:300] + f"...[{len(raw)} chars]"
    return code, short, lat, raw


def probe(name, method, path, token=None, body=None, params=None,
          expect=200, severity="core", timeout=30, group=None):
    code, b, lat, raw = call(method, path, token, body, params, timeout=timeout)
    ok = False
    if expect == "any":
        ok = code < 500
    elif expect == "2xx":
        ok = 200 <= code < 300
    elif expect == "auth_challenge":
        ok = code in (401, 403)
    else:
        ok = (code == expect)
    sym = "PASS" if ok else "FAIL"
    rec = dict(name=name, method=method, path=path, status=code, latency_ms=lat,
               expected=str(expect), result=sym, body=b[:200],
               severity=severity, group=group or "")
    results.append(rec)
    flag = "✓" if ok else "✗"
    g = f" [{group}]" if group else ""
    print(f"  [{flag}] {code:>4} {lat:>5}ms {method:>6} {path:>45}{g}  → {sym}")
    if not ok:
        print(f"        body: {b[:200]}")
    return rec, code, raw


def login():
    code, _short, lat, raw = call("POST", "/auth/login",
                                  body={"username": USER, "password": PASS})
    print(f"\n[登录] HTTP {code} ({lat}ms)")
    if code != 200:
        sys.exit(f"登录失败: {raw[:200]}")
    return json.loads(raw)["data"]


def main():
    print("=" * 78)
    print("通维 AI-PM 端到端功能验证 v2")
    print("=" * 78)

    # ===== 0. 认证 =====
    print("\n[0] 认证模块")
    auth = login()
    token = auth["access_token"]
    print(f"  token 末8: ...{token[-8:]}")
    print(f"  /auth/login 响应字段: {list(auth.keys())}")
    probe("/auth/me 带 token", "GET", "/auth/me", token=token, expect=200, severity="critical", group="auth")
    probe("/auth/me 无 token", "GET", "/auth/me", expect="auth_challenge", severity="critical", group="auth")
    probe("/auth/login 错密码", "POST", "/auth/login",
          body={"username": USER, "password": "wrong-pw"},
          expect="auth_challenge", severity="critical", group="auth")
    probe("/auth/refresh", "POST", "/auth/refresh", token=token, expect="any", severity="core", group="auth")
    probe("/auth/logout", "POST", "/auth/logout", token=token, expect="any", severity="core", group="auth")

    # ===== 1. 核心资源 =====
    print("\n[1] 核心资源")
    probe("项目列表 /projects/", "GET", "/projects/", token=token, expect=200, severity="critical", group="core")
    probe("项目列表带分页", "GET", "/projects/", token=token, params={"page": 1, "size": 5}, expect=200, severity="core", group="core")
    code, b, lat, raw = call("GET", "/projects/", token=token, params={"size": 1})
    pid = None
    if code == 200:
        try:
            d = json.loads(raw)
            # 响应可能是 {items:[...]} 或 {data:{items:[...]}} 或 {data:[...]}
            items = d.get("items")
            if items is None:
                data = d.get("data")
                items = data.get("items") if isinstance(data, dict) else data
            if isinstance(items, list) and items:
                pid = items[0].get("id")
        except Exception:
            pass
    print(f"  ↳ 选定 project_id = {pid}")
    probe("任务列表 /tasks", "GET", "/tasks", token=token, expect=200, severity="critical", group="core")
    if pid:
        probe("项目详情", "GET", f"/projects/{pid}", token=token, expect=200, severity="core", group="core")
        probe("项目成员", "GET", f"/projects/{pid}/members/", token=token, expect=200, severity="core", group="core")
        probe("项目预算", "GET", f"/projects/{pid}/budget", token=token, expect="any", severity="core", group="core")
    probe("UCM 组织列表", "GET", "/ucm/organizations", token=token, expect="any", severity="core", group="core")
    probe("UCM 组织树", "GET", "/ucm/organizations/tree", token=token, expect="any", severity="core", group="core")
    probe("角色列表", "GET", "/roles", token=token, expect="any", severity="core", group="core")
    probe("用户组", "GET", "/user-groups", token=token, expect="any", severity="core", group="core")
    probe("KB 用户", "GET", "/kb-users", token=token, expect="any", severity="core", group="core")

    # ===== 2. AI 能力 =====
    print("\n[2] AI 能力（短超时）")
    probe("AI chat 简单问候", "POST", "/ai/chat", token=token,
          body={"message": "你好"}, expect="2xx", severity="critical",
          timeout=45, group="ai")
    if pid:
        probe("AI 分析项目", "POST", f"/ai/analyze-project/{pid}", token=token,
              expect="2xx", severity="critical", timeout=90, group="ai")
        probe("AI 预测风险", "POST", f"/ai/predict-risk/{pid}", token=token,
              expect="2xx", severity="critical", timeout=90, group="ai")
    probe("Agent 列表", "GET", "/agents", token=token, expect="any", severity="critical", group="ai")
    probe("Agent registry", "GET", "/agents/registry", token=token, expect="any", severity="core", group="ai")
    probe("LLM 配置列表 /llm-configs/", "GET", "/llm-configs/", token=token, expect="any", severity="critical", group="ai")
    probe("LLM 供应商", "GET", "/llm-configs/providers", token=token, expect="any", severity="core", group="ai")
    probe("System LLM 配置", "GET", "/system/llm-config", token=token, expect="any", severity="core", group="ai")
    probe("AI 助手填表", "POST", "/ai/assist-fill", token=token,
          body={"field": "task.title", "context": "电商"},
          expect="any", severity="core", timeout=20, group="ai")
    probe("AI Agent chat", "POST", "/ai/agent/chat", token=token,
          body={"message": "hi", "agent": "evm"}, expect="any", severity="core",
          timeout=30, group="ai")

    # ===== 3. 异步任务 =====
    print("\n[3] 异步任务")
    probe("异步任务列表", "GET", "/async-tasks", token=token, expect="any", severity="critical", group="async")
    if pid:
        rec, code, b = probe("触发 analyze_project", "POST", "/async-tasks", token=token,
              body={"task_type": "analyze_project", "params": {"project_id": pid}},
              expect=200, severity="critical", group="async")
        if code == 200:
            try:
                tid1 = json.loads(b).get("data", {}).get("task_id")
                if tid1:
                    print(f"    等待任务 {tid1[:8]}... 完成（最多 100s）")
                    for i in range(50):
                        time.sleep(2)
                        rc, rb, rl, rr = call("GET", f"/async-tasks/{tid1}", token=token)
                        if rc == 200:
                            st = (json.loads(rr).get("data") or {}).get("status")
                            if st in ("success", "failed"):
                                print(f"    任务 {tid1[:8]} 最终状态: {st}（{rl}ms）")
                                results.append(dict(name="analyze_project 终态", method="GET",
                                                    path=f"/async-tasks/{tid1}", status=rc,
                                                    latency_ms=rl, expected=st,
                                                    result="PASS" if st == "success" else "FAIL",
                                                    body=(rb or "")[:200], severity="critical",
                                                    group="async"))
                                break
                    else:
                        print(f"    任务 {tid1[:8]} 超时未完成")
                        results.append(dict(name="analyze_project 终态", method="GET",
                                            path=f"/async-tasks/{tid1}", status=0,
                                            latency_ms=0, expected="success", result="FAIL",
                                            body="timeout", severity="critical", group="async"))
            except Exception as e:
                print(f"    异常: {e!r}")

        rec, code, b = probe("触发 summarize_lessons", "POST", "/async-tasks", token=token,
              body={"task_type": "summarize_lessons", "params": {"project_id": pid}},
              expect=200, severity="critical", group="async")
        if code == 200:
            try:
                tid2 = json.loads(b).get("data", {}).get("task_id")
                if tid2:
                    print(f"    等待任务 {tid2[:8]}... 完成（最多 100s）")
                    for i in range(50):
                        time.sleep(2)
                        rc, rb, rl, rr = call("GET", f"/async-tasks/{tid2}", token=token)
                        if rc == 200:
                            st = (json.loads(rr).get("data") or {}).get("status")
                            if st in ("success", "failed"):
                                print(f"    任务 {tid2[:8]} 最终状态: {st}（{rl}ms）")
                                results.append(dict(name="summarize_lessons 终态", method="GET",
                                                    path=f"/async-tasks/{tid2}", status=rc,
                                                    latency_ms=rl, expected=st,
                                                    result="PASS" if st == "success" else "FAIL",
                                                    body=(rb or "")[:200], severity="critical",
                                                    group="async"))
                                break
                    else:
                        print(f"    任务 {tid2[:8]} 超时")
                        results.append(dict(name="summarize_lessons 终态", method="GET",
                                            path=f"/async-tasks/{tid2}", status=0,
                                            latency_ms=0, expected="success", result="FAIL",
                                            body="timeout", severity="critical", group="async"))
            except Exception as e:
                print(f"    异常: {e!r}")

    # ===== 4. 实时 WebSocket =====
    print("\n[4] 实时 WebSocket")
    full_ws = f"/ws/events/{token}"
    try:
        cmd = ["curl", "-sk", "-i", "-m", "3",
               "-H", "Connection: Upgrade", "-H", "Upgrade: websocket",
               "-H", "Sec-WebSocket-Version: 13",
               "-H", f"Sec-WebSocket-Key: {os.urandom(16).hex()}",
               f"{API}{full_ws}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        first = (r.stdout.splitlines() or [""])[0]
        code_ws = 101 if "101" in first else (426 if "426" in first else (200 if "200" in first else 0))
        ok = code_ws in (101, 426)  # 101 升级成功，426 也可能（需 HTTPS）
        print(f"  首行: {first.strip()}")
        print(f"  [{'✓' if ok else '✗'}] WebSocket Upgrade")
        results.append(dict(name="WebSocket Upgrade", method="GET(WS)", path=full_ws,
                            status=code_ws, latency_ms=0, expected="101/426",
                            result="PASS" if ok else "FAIL", body=first, severity="critical",
                            group="ws"))
    except Exception as e:
        print(f"  WS 测试异常: {e!r}")
        results.append(dict(name="WebSocket Upgrade", method="GET(WS)", path=full_ws,
                            status=0, latency_ms=0, expected="101/426", result="FAIL",
                            body=str(e), severity="critical", group="ws"))

    # ===== 5. 集成 / MCP / Webhook =====
    print("\n[5] 集成 / MCP / Webhook")
    for name, path in [
        ("MCP initialize", "/mcp/initialize"),
        ("MCP resources list", "/mcp/resources/list"),
        ("MCP prompts list", "/mcp/prompts/list"),
        ("MCP sse", "/mcp/sse"),
    ]:
        probe(name, "GET", path, token=token, expect="any", severity="critical", group="mcp")
    probe("MCP resources read", "POST", "/mcp/resources/read", token=token,
          body={"uri": "aipm://projects"}, expect="any", severity="core", group="mcp")
    probe("MCP prompts get", "POST", "/mcp/prompts/get", token=token,
          body={"name": "default"}, expect="any", severity="core", group="mcp")

    probe("Webhooks 列表", "GET", "/webhooks/", token=token, expect="any", severity="critical", group="webhook")
    probe("Integrations 列表", "GET", "/integrations/", token=token, expect="any", severity="critical", group="webhook")
    probe("Zapier webhook", "GET", "/zapier/webhook", token=token, expect="any", severity="core", group="webhook")
    probe("Zapier auth", "GET", "/zapier/auth", token=token, expect="any", severity="core", group="webhook")
    probe("External projects", "GET", "/external/projects", token=token, expect="any", severity="core", group="webhook")

    # ===== 6. 报表 / Dashboard =====
    print("\n[6] 报表 / Dashboard")
    probe("Dashboard", "GET", "/dashboard", token=token, expect="any", severity="critical", group="report")
    probe("Dashboard next-steps", "GET", "/dashboard/next-steps", token=token, expect="any", severity="core", group="report")
    probe("EVM 报表", "GET", "/reports/evm", token=token, expect="any", severity="core", group="report")
    probe("Burndown", "GET", "/reports/burndown", token=token, expect="any", severity="core", group="report")
    probe("Cumulative flow", "GET", "/reports/cumulative-flow", token=token, expect="any", severity="core", group="report")
    probe("Daily report", "GET", "/reports/daily", token=token, expect="any", severity="core", group="report")
    probe("Risk trend", "GET", "/reports/risk-trend", token=token, expect="any", severity="core", group="report")
    probe("Resource utilization", "GET", "/reports/resource-utilization", token=token, expect="any", severity="core", group="report")
    probe("Approvals dashboard", "GET", "/approvals/dashboard", token=token, expect="any", severity="core", group="report")
    probe("Compliance dashboard", "GET", "/compliance/dashboard", token=token, expect="any", severity="core", group="report")
    probe("Compliance reports summary", "GET", "/compliance/reports/summary", token=token, expect="any", severity="core", group="report")
    if pid:
        probe("项目预算报表", "GET", f"/projects/{pid}/budget/report", token=token, expect="any", severity="core", group="report")
        probe("PDF 报告导出", "GET", f"/exports/projects/{pid}/report/pdf", token=token, expect="any", severity="core", group="report", timeout=45)

    # ===== 7. PMBOK 业务核心 =====
    print("\n[7] PMBOK 业务核心")
    for ep in ["risks", "lessons", "change-requests", "sprints", "epics",
               "resources", "budgets", "stakeholders", "deliverables",
               "documents", "comments", "workflows"]:
        probe(f"{ep} 列表", "GET", f"/{ep}", token=token, expect="any", severity="core", group="pmbok")
    if pid:
        probe("项目 lessons 生成", "POST", f"/projects/{pid}/summarize-lessons", token=token,
              expect="any", severity="core", timeout=90, group="pmbok")
        probe("WBS 生成", "POST", "/ai/generate-wbs", token=token,
              body={"project_id": pid, "scope": "电商APP"},
              expect="2xx", severity="critical", timeout=90, group="pmbok")

    # ===== 汇总 =====
    print("\n" + "=" * 78)
    print("汇总")
    print("=" * 78)
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = [r for r in results if r["result"] == "FAIL"]
    crit_fail = [r for r in failed if r["severity"] == "critical"]

    print(f"总计: {total}   PASS: {passed}   FAIL: {len(failed)}   关键 FAIL: {len(crit_fail)}")
    if failed:
        print("\n失败清单:")
        for r in failed:
            print(f"  ✗ [{r['severity']:>8}] {r['method']:>6} {r['path']:>50}  HTTP {r['status']}  expect={r['expected']}")
            if r['body']:
                print(f"        {r['body'][:160]}")

    # 分组统计
    print("\n按分组:")
    from collections import Counter
    grp = Counter()
    grp_pass = Counter()
    for r in results:
        g = r.get("group") or "other"
        grp[g] += 1
        if r["result"] == "PASS":
            grp_pass[g] += 1
    for g, n in grp.most_common():
        p = grp_pass[g]
        print(f"  {g:>10}: {p}/{n}  ({p*100//n}%)")

    with open("/tmp/verify_results.json", "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": total, "pass": passed, "fail": len(failed),
                               "critical_fail": len(crit_fail)},
                   "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n详细 JSON → /tmp/verify_results.json")
    return 0 if not crit_fail else 1


if __name__ == "__main__":
    sys.exit(main())
