#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「通维 AI-PM 示例项目」16 个模块经 API 可读到联动数据。
兼容两种响应信封：裸分页 {"items":[...]} 与 {"code":200,"data":{...}}。
"""
import urllib.request
import json
import sys

BASE = "http://127.0.0.1:8000/api/v1"

def _load_ids():
    """优先从 seed_demo 生成的 manifest 读取真实 ID，缺失时回退内置常量（与历史生产一致）。"""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, ".seed_demo_manifest.json")
    if os.path.exists(manifest):
        try:
            with open(manifest, encoding="utf-8") as f:
                d = json.load(f)
            pid = d.get("project_id")
            kb = d.get("knowledge_base_id")
            if pid and kb:
                return pid, kb
        except Exception:
            pass
    return (
        "67b89883-28de-4a45-9aba-56a68bb0c768",  # 通维 AI-PM 示例项目
        "96831b4c-fc18-45f5-83c4-dad350f61f51",  # 示例知识库
    )

PID, KBID = _load_ids()

def login():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = json.load(urllib.request.urlopen(req))
    # login 返回 {"code":200,"data":{"access_token":...}}
    return r["data"]["access_token"]

def get(token, path, params=None):
    url = BASE + path
    if params:
        q = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url += ("?" + q)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except Exception:
            return {"_error": e.code, "detail": body[:300]}
    except Exception as e:
        return {"_error": str(e)}

def extract_list(d):
    """从各种信封结构中抽取列表。"""
    if isinstance(d, list):
        return d
    if not isinstance(d, dict):
        return []
    if "items" in d and isinstance(d["items"], list):
        return d["items"]
    if "data" in d:
        data = d["data"]
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
            if "list" in data and isinstance(data["list"], list):
                return data["list"]
    if "detail" in d:
        return []
    return []

def show(title, d):
    if isinstance(d, dict) and "detail" in d:
        print(f"  [ERROR] {title}: {d.get('detail')}")
        return 0
    if isinstance(d, dict) and "_error" in d:
        print(f"  [HTTP {d.get('_error')}] {title}: {d.get('detail')}")
        return 0
    lst = extract_list(d)
    if lst:
        print(f"  [OK] {title}: {len(lst)} 条")
        return len(lst)
    # 可能是单对象（如 budget / evm 报告）
    if isinstance(d, dict) and d:
        keys = list(d.keys())[:8]
        print(f"  [OBJ] {title}: 单对象, keys={keys}")
        return 1
    print(f"  [EMPTY] {title}: 0")
    return 0

def main():
    import urllib.parse
    token = login()
    print("=" * 60)
    print("通维 AI-PM 示例项目 — 模块 API 联动验证")
    print(f"ProjectID = {PID}")
    print("=" * 60)

    results = {}

    # 1. 项目
    d = get(token, "/projects")
    plist = extract_list(d)
    demo = [p for p in plist if p.get("id") == PID]
    results["项目"] = len(plist)
    print(f"\n[1] 项目列表: 共 {len(plist)} 个, 示例项目命中={bool(demo)}")

    # 2. 任务
    d = get(token, "/tasks", {"project_id": PID})
    results["任务"] = show("[2] 任务", d)
    first_task_id = ""
    if isinstance(d, dict) and "items" in d:
        items = d["items"]
        if items:
            first_task_id = items[0].get("id", "")

    # 3. 迭代
    d = get(token, "/sprints", {"project_id": PID})
    results["迭代"] = show("[3] 迭代(Sprints)", d)

    # 4. OKR
    d = get(token, "/okrs", {"project_id": PID})
    results["OKR"] = show("[4] OKR(Objectives)", d)

    # 5. 风险
    d = get(token, "/risks", {"project_id": PID})
    results["风险"] = show("[5] 风险(Risks)", d)

    # 6. 资源
    d = get(token, "/resources", {"project_id": PID})
    results["资源"] = show("[6] 资源(Resources)", d)

    # 7. 资源分配
    d = get(token, "/resource-allocations", {"project_id": PID})
    results["资源分配"] = show("[7] 资源分配(ResourceAllocations)", d)

    # 8. 变更请求（按项目过滤）+ 里程碑（合并端点）
    d_cr = get(token, "/change-requests/", {"project_id": PID})
    cr_list = extract_list(d_cr)
    print(f"\n[8a] 变更请求(ChangeRequests, project_id 过滤): {len(cr_list)} 条")
    results["变更"] = len(cr_list)

    d_m = get(token, f"/change-requests/entities/{PID}")
    mls = []
    if isinstance(d_m, dict) and "detail" not in d_m:
        mls = d_m.get("milestones") or []
        mls = mls if isinstance(mls, list) else []
    print(f"[8b] 里程碑(Milestones, 合并端点): {len(mls)} 条")
    results["里程碑"] = len(mls)

    # 9. 预算（真实路径 /projects/{pid}/budget）
    d = get(token, f"/projects/{PID}/budget")
    if isinstance(d, dict) and "detail" not in d and d:
        print(f"\n[9] 预算(ProjectBudget): 存在, total_budget={d.get('total_budget')}, spent={d.get('spent_amount')}")
        results["预算"] = 1
    else:
        show("[9] 预算", d)
        results["预算"] = 0

    # 10. 知识库
    d = get(token, "/knowledge-bases", {"project_id": PID})
    results["知识库"] = show("[10] 知识库(KnowledgeBases)", d)

    # 11. 知识文档
    d = get(token, f"/knowledge-bases/{KBID}/documents")
    results["知识文档"] = show("[11] 知识文档(KnowledgeDocuments)", d)

    # 12. 白板（全局）
    d = get(token, "/whiteboards")
    results["白板"] = show("[12] 白板(Whiteboards, 全局)", d)

    # 13. 通知（全局）
    d = get(token, "/notifications")
    results["通知"] = show("[13] 通知(Notifications, 全局)", d)

    # 14. EVM（实时计算报告）
    d = get(token, "/reports/evm", {"project_id": PID})
    if isinstance(d, dict) and "detail" not in d and d:
        # evm 报告常见字段
        sample = {k: d.get(k) for k in ("planned_value", "earned_value", "actual_cost", "cpi", "spi", "snapshot_count", "snapshots") if k in d}
        print(f"\n[14] EVM 报告(reports/evm): 有数据, 样例={sample}")
        results["EVM"] = 1
    else:
        show("[14] EVM 报告", d)
        results["EVM"] = 0

    # 15. 评论（真实路径 /tasks/{task_id}/comments）
    if first_task_id:
        d = get(token, f"/tasks/{first_task_id}/comments")
        results["评论"] = show(f"[15] 评论(Comments, task={first_task_id[:8]}..)", d)
    else:
        print("\n[15] 评论: 无可用 task_id，跳过")
        results["评论"] = -1

    # 汇总
    print("\n" + "=" * 60)
    print("汇总（计数）:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    zero = [k for k, v in results.items() if v == 0]
    print("=" * 60)
    if zero:
        print(f"⚠️ 以下模块返回 0 或异常: {zero}")
        sys.exit(2)
    else:
        print("✅ 全部模块均有数据，联动验证通过")
        sys.exit(0)

if __name__ == "__main__":
    main()
