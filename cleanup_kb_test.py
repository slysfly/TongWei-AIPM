# -*- coding: utf-8 -*-
"""清理生产环境遗留的 KB / 用户组测试产物（按名称模式，仅 admin 创建）。"""
import json, urllib.request, urllib.error, ssl, re, sys
BASE = "https://81.70.158.130"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
def req(method, path, token=None, body=None):
    headers = {}
    data = None
    if token: headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode("utf-8"); headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30, context=ctx) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

pat = re.compile(r"验证|终检|轻量|全格式|自动清理|确认库|系统自动知识库")
st, raw = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
tok = json.loads(raw)["data"]["access_token"]
print("== 清理遗留 KB ==")
st, raw = req("GET", "/api/v1/knowledge-bases?scope=all", tok)
for k in (json.loads(raw) if raw else []):
    if pat.search(k.get("name", "")):
        st2, _ = req("DELETE", "/api/v1/knowledge-bases/%s" % k["id"], tok)
        print("  删除KB:", k["name"], "->", st2)
print("== 清理遗留用户组 ==")
st, raw = req("GET", "/api/v1/user-groups", tok)
for g in (json.loads(raw) if raw else []):
    if pat.search(g.get("name", "")):
        st2, _ = req("DELETE", "/api/v1/user-groups/%s" % g["id"], tok)
        print("  删除组:", g["name"], "->", st2)
print("== DONE ==")
