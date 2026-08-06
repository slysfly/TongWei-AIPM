#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境知识库增强功能端到端验证：
登录 -> 用户组 -> 建库 -> 分享(用户组) -> 批量上传(txt+docx) -> 检索 -> RAG上下文
仅在已部署的生产服务器 (81.70.158.130) 上运行。
"""
import json
import io
import os
import random
import ssl
import string
import sys
import urllib.error
import urllib.request
import zipfile

BASE = "https://81.70.158.130"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def req(method, path, token=None, body=None, files=None, timeout=90):
    url = BASE + path
    if files is not None:
        boundary = "----bnd" + "".join(random.choice(string.ascii_letters) for _ in range(12))
        parts = []
        for (field, fname, data, ctype) in files:
            parts.append(("--" + boundary).encode())
            parts.append(('Content-Disposition: form-data; name="%s"; filename="%s"' % (field, fname)).encode())
            parts.append(("Content-Type: %s" % ctype).encode())
            parts.append(b"")
            parts.append(data)
        parts.append(("--" + boundary + "--").encode())
        parts.append(b"")
        data = b"\r\n".join(parts)
        headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}
        if token:
            headers["Authorization"] = "Bearer " + token
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
    else:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return -1, "EXC:%s:%s" % (type(e).__name__, e)


def get_uid(login_body):
    if isinstance(login_body, dict):
        for key in ("user", "data"):
            sub = login_body.get(key)
            if isinstance(sub, dict):
                if sub.get("id"):
                    return sub["id"]
                if isinstance(sub.get("user"), dict) and sub["user"].get("id"):
                    return sub["user"]["id"]
        if login_body.get("id"):
            return login_body["id"]
    return None


def build_docx(text):
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>" + text + "</w:t></w:r></w:p></w:body></w:document>"
    ).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types/>')
        z.writestr("_rels/.rels", b'<?xml version="1.0"?><Relationships/>')
        z.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


def main():
    print("== 1) 登录 admin ==")
    st, body = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": "admin123"})
    print("  login:", st)
    if st not in (200, 201):
        print("  登录失败，响应:", str(body)[:200]); return
    token = None
    if isinstance(body, dict):
        token = body.get("access_token") or body.get("token")
        if not token and isinstance(body.get("data"), dict):
            token = body["data"].get("access_token")
    print("  token:", "OK" if token else "无")
    if not token:
        print("  无 token，响应:", str(body)[:300]); return
    uid = get_uid(body)
    if not uid:
        st, me = req("GET", "/api/v1/auth/me", token=token)
        if st == 200 and isinstance(me, dict):
            uid = me.get("id") or (me.get("data") or {}).get("id")
    print("  admin uid:", uid)

    print("== 2) GET /kb-users ==")
    st, body = req("GET", "/api/v1/kb-users", token=token)
    print("  kb-users:", st, "count=", len(body) if isinstance(body, list) else body)

    print("== 3) 创建用户组 ==")
    st, body = req("POST", "/api/v1/user-groups", token=token,
                   body={"name": "验证组_自动", "description": "端到端自动验证用"})
    print("  create-group:", st, body if st == 201 else str(body)[:200])
    gid = body.get("id") if isinstance(body, dict) else None

    if gid and uid:
        print("== 4) 加入成员(admin) ==")
        st, body = req("POST", "/api/v1/user-groups/%s/members" % gid, token=token,
                       body={"user_id": uid})
        print("  add-member:", st, str(body)[:150])
        st, body = req("GET", "/api/v1/user-groups/%s" % gid, token=token)
        print("  get-group members:", st, (body.get("members") if isinstance(body, dict) else body))

    print("== 5) 创建知识库 ==")
    import time as _t
    kb_name = "验证知识库_自动_%d" % int(_t.time())
    st, body = req("POST", "/api/v1/knowledge-bases/", token=token,
                   body={"name": kb_name, "description": "端到端自动验证"})
    print("  create-kb:", st)
    kb_id = body.get("id") if isinstance(body, dict) else None
    print("  kb_id:", kb_id)

    if kb_id and gid:
        print("== 6) 分享给(用户组) ==")
        st, body = req("POST", "/api/v1/knowledge-bases/%s/shares" % kb_id, token=token,
                       body={"share_type": "group", "target_id": gid, "permission": "read"})
        print("  add-share(group):", st, str(body)[:200])
        st, body = req("GET", "/api/v1/knowledge-bases/%s/shares" % kb_id, token=token)
        print("  list-shares:", st, "count=", len(body) if isinstance(body, list) else body)

    if kb_id:
        print("== 7) 批量上传 txt + docx ==")
        docx_bytes = build_docx("通维AI-PM知识库自动验证文档，包含项目里程碑与风险登记内容。")
        files = [
            ("files", "说明.txt", "这是一段测试文本，用于验证RAG自动解析与分块。".encode("utf-8"), "text/plain"),
            ("files", "纪要.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]
        st, body = req("POST", "/api/v1/knowledge-bases/%s/documents/upload-batch" % kb_id, token=token, files=files, timeout=260)
        print("  upload-batch:", st)
        if isinstance(body, list):
            for r in body:
                print("    -", r.get("file_name"), r.get("status"), "chunks=", r.get("chunk_count"), "err=", r.get("error"))
        else:
            print("    响应:", str(body)[:300])

        print("== 8) 检索 ==")
        st, body = req("POST", "/api/v1/knowledge-bases/%s/search" % kb_id, token=token,
                       body={"query": "项目里程碑", "top_k": 3})
        print("  search:", st, "hits=", (len(body.get("results", [])) if isinstance(body, dict) else body))

        print("== 9) RAG 上下文 ==")
        st, body = req("POST", "/api/v1/knowledge-bases/rag/context", token=token,
                       body={"query": "风险登记", "kb_ids": [kb_id], "top_k": 3})
        print("  rag-context:", st, "len=", (len(body.get("context", "")) if isinstance(body, dict) else body))

    print("== 10) 清理测试产物 ==")
    if kb_id:
        st, _ = req("DELETE", "/api/v1/knowledge-bases/%s" % kb_id, token=token)
        print("  delete-kb:", st)
    if gid:
        st, _ = req("DELETE", "/api/v1/user-groups/%s" % gid, token=token)
        print("  delete-group:", st)

    print("== DONE ==")


if __name__ == "__main__":
    main()
