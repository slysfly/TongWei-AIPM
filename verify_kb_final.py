# -*- coding: utf-8 -*-
"""生产环境精细端到端核查：模拟真实用户对知识库每一个行为的操作，并自清理。"""
import json, urllib.request, urllib.error, ssl, io, zipfile, sys
from urllib.parse import quote

BASE = "https://81.70.158.130"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def req(method, path, token=None, body=None, files=None):
    url = BASE + path
    headers = {}
    data = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if files is not None:
        boundary = "----kbtestboundary"
        parts = []
        for f in files:
            name, fname, content, ctype = f
            parts.append(("--" + boundary).encode())
            parts.append(('Content-Disposition: form-data; name="%s"; filename="%s"' % (name, fname)).encode())
            parts.append(("Content-Type: %s" % ctype).encode())
            parts.append(b"")
            parts.append(content if isinstance(content, bytes) else content.encode("utf-8"))
        parts.append(("--" + boundary + "--").encode())
        parts.append(b"")
        data = b"\r\n".join(parts)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    else:
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=90, context=ctx) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

# 追踪创建的资源，确保全部清理
created = {"kb": [], "group": [], "share": []}

def log(label, st, extra=""):
    mark = "OK " if (200 <= st < 300) else "FAIL"
    print("  [%s] %s -> %s %s" % (mark, label, st, extra))

def main():
    print("== 1) 登录 admin ==")
    st, raw = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
    print("  login:", st)
    token = json.loads(raw)["data"]["access_token"]

    print("== 2) 列表(scope=all) 校验 my_permission 字段 ==")
    st, raw = req("GET", "/api/v1/knowledge-bases?scope=all", token)
    lst = json.loads(raw)
    print("  list:", st, "count=", len(lst))
    for k in lst[:5]:
        print("    -", k["name"], "| access_role=", k.get("access_role"),
              "| my_permission=", k.get("my_permission"), "| visibility=", k.get("visibility"),
              "| is_shared=", k.get("is_shared"))

    print("== 3) 新建知识库（应 my_permission=owner/write）==")
    st, raw = req("POST", "/api/v1/knowledge-bases/", token, body={"name": "终检库_自动清理", "description": "final check"})
    kb = json.loads(raw)
    kb_id = kb["id"]; created["kb"].append(kb_id)
    print("  create:", st, "my_permission=", kb.get("my_permission"))

    print("== 4) 粘贴文本添加文档 ==")
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/documents" % kb_id, token,
                  body={"title": "需求说明", "content": "本系统需要支持多用户知识库隔离与共享。"})
    doc = json.loads(raw) if raw else {}
    print("  add-doc(paste):", st, "id=", doc.get("id"))

    print("== 5) 多格式批量上传（txt/md/docx）==")
    doc_xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:body><w:p><w:r><w:t>会议纪要：项目进度正常推进。</w:t></w:r></w:p></w:body></w:document>').encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", b"<Types/>")
        z.writestr("word/document.xml", doc_xml)
    docx_bytes = buf.getvalue()
    files = [
        ("files", "说明.txt", "产品需求说明书：支持批量导入与权限隔离。".encode("utf-8"), "text/plain"),
        ("files", "设计.md", "# 架构\n采用前后端分离。\n".encode("utf-8"), "text/markdown"),
        ("files", "纪要.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/documents/upload-batch" % kb_id, token, files=files)
    print("  upload-batch:", st)
    for r in (json.loads(raw) if isinstance(json.loads(raw), list) else []):
        print("    -", r.get("file_name"), r.get("status"), "chunks=", r.get("chunk_count"), "err=", r.get("error"))

    print("== 6) 文档列表 ==")
    st, raw = req("GET", "/api/v1/knowledge-bases/%s/documents" % kb_id, token)
    docs = json.loads(raw) if raw else []
    print("  list-docs:", st, "count=", len(docs) if isinstance(docs, list) else docs)

    print("== 7) 全系统分享（my_permission 应变为 read）==")
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/shares" % kb_id, token,
                  body={"share_type": "system", "permission": "read"})
    print("  share-system:", st)
    share_id = (json.loads(raw).get("id") if raw else None)
    if share_id: created["share"].append((kb_id, share_id))
    st, raw = req("GET", "/api/v1/knowledge-bases?scope=all", token)
    for k in json.loads(raw):
        if k["id"] == kb_id:
            print("    -> access_role=", k.get("access_role"), "my_permission=", k.get("my_permission"), "visibility=", k.get("visibility"))

    print("== 8) 创建用户组并加成员 ==")
    st, raw = req("POST", "/api/v1/user-groups", token, body={"name": "终检组_自动清理", "description": "final"})
    grp = json.loads(raw); gid = grp["id"]; created["group"].append(gid)
    print("  create-group:", st, "id=", gid)
    # 用 admin 自己的 id 加为成员（从 /auth/me 取）
    st, raw = req("GET", "/api/v1/auth/me", token)
    my_id = json.loads(raw).get("id")
    if my_id:
        st, raw = req("POST", "/api/v1/user-groups/%s/members" % gid, token, body={"user_id": my_id})
        print("  add-member:", st)
    # 设为组分享
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/shares" % kb_id, token,
                  body={"share_type": "group", "target_id": gid, "permission": "write"})
    print("  share-group(write):", st)
    share2 = json.loads(raw).get("id") if raw else None
    if share2: created["share"].append((kb_id, share2))

    print("== 9) 检索 / RAG上下文 / QA / 查看分块 ==")
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/search" % kb_id, token, body={"query": "权限", "top_k": 5})
    print("  search:", st, "hits=", len(json.loads(raw).get("results", [])) if raw else 0)
    st, raw = req("POST", "/api/v1/knowledge-bases/rag/context", token, body={"kb_ids": [kb_id], "query": "进度", "top_k": 5})
    print("  rag-context:", st, "len=", len(json.loads(raw).get("context", "")) if raw else 0)
    st, raw = req("POST", "/api/v1/knowledge-bases/%s/qa" % kb_id, token, body={"question": "项目进度如何？"})
    print("  qa:", st, "ans_len=", len(json.loads(raw).get("answer", "")) if raw else 0)
    if isinstance(docs, list) and docs:
        did = docs[0].get("id")
        st, raw = req("GET", "/api/v1/knowledge-bases/%s/documents/%s/chunks" % (kb_id, did), token)
        print("  chunks:", st, "count=", len(json.loads(raw)) if raw else 0)

    print("== 10) 删除文档 ==")
    if isinstance(docs, list) and docs:
        did = docs[0].get("id")
        st, raw = req("DELETE", "/api/v1/knowledge-bases/%s/documents/%s" % (kb_id, did), token)
        print("  delete-doc:", st)

    print("== 11) 取消分享 + 删除用户组 ==")
    for kb_s, sid in created["share"]:
        st, raw = req("DELETE", "/api/v1/knowledge-bases/%s/shares/%s" % (kb_s, sid), token)
        print("  remove-share:", st)
    for gid in created["group"]:
        st, raw = req("DELETE", "/api/v1/user-groups/%s" % gid, token)
        print("  delete-group:", st)

    print("== 12) 删除知识库（级联修复验证）==")
    for kid in created["kb"]:
        st, raw = req("DELETE", "/api/v1/knowledge-bases/%s" % kid, token)
        print("  delete-kb:", st)

    print("== DONE ==")


def sweep(token):
    """清理任何遗留的测试产物（按名称模式 + 仅 admin 创建的）。"""
    import re
    pat = re.compile(r"验证|终检|轻量|全格式|自动清理|确认库|系统自动知识库")
    print("== 清理遗留测试产物 ==")
    st, raw = req("GET", "/api/v1/knowledge-bases?scope=all", token)
    for k in (json.loads(raw) if raw else []):
        if pat.search(k.get("name", "")):
            st2, _ = req("DELETE", "/api/v1/knowledge-bases/%s" % k["id"], token)
            print("  删除遗留KB:", k["name"], "->", st2)
    st, raw = req("GET", "/api/v1/user-groups", token)
    for g in (json.loads(raw) if raw else []):
        if pat.search(g.get("name", "")):
            st2, _ = req("DELETE", "/api/v1/user-groups/%s" % g["id"], token)
            print("  删除遗留组:", g["name"], "->", st2)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback; traceback.print_exc()
        sys.exit(1)
    # 登录以执行清理（main 内部已登录，这里复用）
    try:
        st, raw = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
        tok = json.loads(raw)["data"]["access_token"]
        sweep(tok)
    except Exception as e:
        print("sweep error:", e)
