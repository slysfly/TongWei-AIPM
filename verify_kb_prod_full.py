import json, io, zipfile, urllib.request, ssl, time

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
BASE = "https://81.70.158.130"

def req(method, path, token=None, body=None, files=None):
    url = BASE + path
    data = None; headers = {}
    if files is not None:
        boundary = "----kbtestboundary"
        parts = []
        for f in files:
            name, content, ctype = f
            parts.append(("--"+boundary).encode())
            parts.append(('Content-Disposition: form-data; name="files"; filename="%s"' % name).encode())
            parts.append(("Content-Type: %s" % ctype).encode())
            parts.append(b""); parts.append(content)
        parts.append(("--"+boundary+"--").encode()); parts.append(b"")
        data = b"\r\n".join(parts)
        headers["Content-Type"] = "multipart/form-data; boundary="+boundary
    elif body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"]="application/json"
    if token: headers["Authorization"]="Bearer "+token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=240, context=ctx) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def jget(raw):
    try: return json.loads(raw)
    except: return raw

print("== 1) 登录 admin ==")
st, raw = req("POST","/api/v1/auth/login", body={"username":"admin","password":"admin123"})
print("  login:", st)
token = jget(raw).get("data",{}).get("access_token")
print("  token:", "OK" if token else "MISSING")

def mk_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,"w") as z:
        z.writestr("[Content_Types].xml", b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>项目风险清单与缓解措施</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()

def mk_xlsx():
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title="预算"
    ws.append(["科目","金额"]); ws.append(["人力",100]); ws.append(["设备",200])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

def mk_pptx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,"w") as z:
        z.writestr("[Content_Types].xml", b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("ppt/slides/slide1.xml", '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>季度复盘要点</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    return buf.getvalue()

print("== 2) 列表(初始) ==")
st, raw = req("GET","/api/v1/knowledge-bases?scope=all", token=token)
lst = jget(raw); print("  list:", st, "count=", len(lst) if isinstance(lst,list) else raw[:80])

print("== 3) 创建知识库 ==")
st, raw = req("POST","/api/v1/knowledge-bases/", token=token, body={"name":"全格式验证库","description":"端到端多格式+QA"})
print("  create-kb:", st)
kb = jget(raw); kb_id = kb.get("id") if isinstance(kb,dict) else None
print("  kb_id:", kb_id, "document_count字段:", kb.get("document_count") if isinstance(kb,dict) else None)

print("== 4) 粘贴文本添加 ==")
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/documents", token=token, body={"title":"登录流程","content":"用户登录需要手机号验证，后台校验token有效期。"})
print("  addDoc(text):", st)

print("== 5) 批量上传多格式 ==")
files = [
    ("说明.txt","产品需求说明书：支持批量导入与权限隔离。".encode("utf-8"),"text/plain"),
    ("设计.md","# 架构\n采用前后端分离。\n".encode("utf-8"),"text/markdown"),
    ("数据.csv","name,age\nAlice,30\nBob,25\n".encode("utf-8"), "text/csv"),
    ("配置.json",'{"key":"value","enabled":true}'.encode("utf-8"),"application/json"),
    ("页面.html","<html><body><p>欢迎使用知识库系统</p></body></html>".encode("utf-8"),"text/html"),
    ("脚本.py","def hello():\n    print('hi')\n".encode("utf-8"),"text/x-python"),
    ("纪要.docx", mk_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("预算.xlsx", mk_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("汇报.pptx", mk_pptx(), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ("二进制.bin", b"\x00\x01\x02\xff\xfe some text fragments".replace(b"fragments", b"fragments"), "application/octet-stream"),
]
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/documents/upload-batch", token=token, files=files)
print("  upload-batch:", st)
res = jget(raw)
if isinstance(res, list):
    for r in res:
        print("    -", r.get("file_name"), r.get("status"), "chunks=", r.get("chunk_count"), "supported=", r.get("supported"), "err=", r.get("error"))
else:
    print("    响应:", str(raw)[:300])

print("== 6) 文档列表 ==")
st, raw = req("GET", f"/api/v1/knowledge-bases/{kb_id}/documents", token=token)
docs = jget(raw); print("  listDocs:", st, "count=", len(docs) if isinstance(docs,list) else raw[:80])
doc_id = docs[0].get("id") if isinstance(docs,list) and docs else None

print("== 7) 检索 ==")
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/search", token=token, body={"query":"风险","top_k":5})
sr = jget(raw); 
print("  search:", st, "total=", (sr.get("total") if isinstance(sr,dict) else None))
if isinstance(sr,dict):
    for h in sr.get("results",[])[:3]:
        print("    hit:", h.get("document_title"), "score=", h.get("score"))

print("== 8) RAG 问答(此前未测) ==")
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/qa", token=token, body={"question":"知识库支持哪些文件格式？","top_k":5})
qa = jget(raw); print("  qa:", st)
if isinstance(qa,dict):
    print("    answer:", (qa.get("answer") or "")[:200])
    print("    sources:", qa.get("sources"))

print("== 9) rag-context(系统级) ==")
st, raw = req("POST","/api/v1/knowledge-bases/rag/context", token=token, body={"query":"风险","kb_ids":[kb_id],"top_k":3})
rc = jget(raw); print("  rag-context:", st, "len=", (len(rc.get("context","")) if isinstance(rc,dict) else raw[:80]))

print("== 10) 查看分块 ==")
if doc_id:
    st, raw = req("GET", f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/chunks", token=token)
    ch = jget(raw); print("  chunks:", st, "n=", len(ch.get("chunks",[])) if isinstance(ch,dict) else raw[:80])
else:
    print("  (无 doc_id 跳过)")

print("== 11) 用户组全流程 ==")
st, raw = req("POST","/api/v1/user-groups", token=token, body={"name":"全格式验证组"})
g = jget(raw); gid = g.get("id") if isinstance(g,dict) else None
print("  create-group:", st, "gid=", gid)
st, raw = req("POST", f"/api/v1/user-groups/{gid}/members", token=token, body={"user_id":"017e5d20-e5f6-4bd7-86ef-0bdce45aca45"})
print("  add-member(self):", st)
st, raw = req("GET", f"/api/v1/user-groups/{gid}", token=token)
print("  get-group:", st, "members=", (jget(raw) or {}).get("members"))

print("== 12) 分享(组+系统) ==")
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/shares", token=token, body={"share_type":"group","target_id":gid,"permission":"read"})
print("  share-group:", st)
st, raw = req("POST", f"/api/v1/knowledge-bases/{kb_id}/shares", token=token, body={"share_type":"system","permission":"read"})
print("  share-system:", st)
st, raw = req("GET", f"/api/v1/knowledge-bases/{kb_id}/shares", token=token)
print("  list-shares:", st, "count=", len(jget(raw)) if isinstance(jget(raw),list) else raw[:80])

print("== 13) 删除文档 ==")
if doc_id:
    st, raw = req("DELETE", f"/api/v1/knowledge-bases/documents/{doc_id}", token=token)
    print("  delete-doc:", st)
else:
    print("  (无 doc_id 跳过)")

print("== 14) 删除知识库 ==")
st, raw = req("DELETE", f"/api/v1/knowledge-bases/{kb_id}", token=token)
print("  delete-kb:", st)
st, raw = req("DELETE", f"/api/v1/user-groups/{gid}", token=token)
print("  delete-group:", st)

print("== DONE ==")
