"""知识库增强（分享/用户组/多格式批量上传）本地验证。"""
import asyncio
import os
import tempfile
import zipfile
import io

# 使用全新临时 sqlite，create_all 建表（含新增 shares/groups 表）
tmp = tempfile.mkdtemp()
DB = os.path.join(tmp, "test_kb.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB}"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import app.models  # 注册全部模型
from app.db.session import Base
from app.models import User
from app.core.security import get_current_user
from app.db.session import get_db
from fastapi import FastAPI
from app.api.routers import api_router

engine = create_async_engine(f"sqlite+aiosqlite:///{DB}", echo=False, future=True)
TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()
app.include_router(api_router, prefix="/api/v1")

# 依赖覆盖：用真实 DB session + 可切换的当前用户
_STATE = {"user": None}
async def _override_db():
    async with TestSession() as s:
        yield s
async def _override_user():
    return _STATE["user"]
app.dependency_overrides[get_db] = _override_db
app.dependency_overrides[get_current_user] = _override_user

from starlette.testclient import TestClient
client = TestClient(app)

def jr(r):
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:200]

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 创建两个用户
    async with TestSession() as s:
        u1 = User(id="u1", email="u1@x.com", username="u1", hashed_password="x", is_active=True)
        u2 = User(id="u2", email="u2@x.com", username="u2", hashed_password="x", is_active=True)
        s.add_all([u1, u2]); await s.commit()

    # 以 u1 操作
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u1"))

    print("== 1) u1 创建知识库 ==")
    st, body = jr(client.post("/api/v1/knowledge-bases/", json={"name": "研发知识库", "description": "d"}))
    print(st, body.get("id")); kb_id = body["id"]

    print("== 2) u1 列表(scope=all) ==")
    st, body = jr(client.get("/api/v1/knowledge-bases/?scope=all"))
    print(st, [(b["name"], b["access_role"], b["visibility"]) for b in body])

    print("== 3) u2 列表(应看不到私有库) ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u2"))
    st, body = jr(client.get("/api/v1/knowledge-bases/?scope=all"))
    print(st, "count=", len(body))

    print("== 4) u1 分享给 u2(read) ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u1"))
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/shares", json={"share_type": "user", "target_id": "u2", "permission": "read"}))
    print(st, body)

    print("== 5) u2 列表(应看到 shared) ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u2"))
    st, body = jr(client.get("/api/v1/knowledge-bases/?scope=all"))
    print(st, [(b["name"], b["access_role"], b["visibility"]) for b in body])

    print("== 6) u2 写文档(应 403) ==")
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", json={"title": "t", "content": "c"}))
    print(st, body)

    print("== 7) u1 改分享为 write ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u1"))
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/shares", json={"share_type": "user", "target_id": "u2", "permission": "write"}))
    print(st)
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u2"))
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/documents", json={"title": "u2写的", "content": "hello world"}))
    print("u2 write ->", st)

    print("== 8) u1 系统级分享 ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u1"))
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/shares", json={"share_type": "system", "permission": "read"}))
    print(st)

    print("== 9) 用户组：创建+加成员 ==")
    st, body = jr(client.post("/api/v1/user-groups", json={"name": "研发组"}))
    print(st, body.get("id")); gid = body["id"]
    st, body = jr(client.post(f"/api/v1/user-groups/{gid}/members", json={"user_id": "u2"}))
    print("add member ->", st)
    st, body = jr(client.get(f"/api/v1/user-groups/{gid}"))
    print("group members ->", [m["username"] for m in body.get("members", [])])

    print("== 10) 批量上传：txt + 伪 docx ==")
    # 构造一个最小 docx
    doc_xml = '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>项目启动会纪要</w:t></w:r></w:p><w:p><w:r><w:t>确定范围与里程碑。</w:t></w:r></w:p></w:body></w:document>'.encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", b"<Types/>")
        z.writestr("word/document.xml", doc_xml)
    docx_bytes = buf.getvalue()
    files = [
        ("files", ("说明.txt", "这是一段测试文本，用于知识库检索验证。".encode("utf-8"), "text/plain")),
        ("files", ("纪要.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/documents/upload-batch", files=files))
    print(st)
    for r in body:
        print("  -", r["file_name"], r["status"], "chunks=", r["chunk_count"], "err=", r.get("error"))

    print("== 11) 检索验证（system 共享下 u2 可用） ==")
    async with TestSession() as s:
        _STATE["user"] = (await s.get(User, "u2"))
    st, body = jr(client.post(f"/api/v1/knowledge-bases/{kb_id}/search", json={"query": "项目启动", "top_k": 3}))
    print("u2 search ->", st, "hits=", len(body.get("results", [])))
    st, body = jr(client.post("/api/v1/knowledge-bases/rag/context", json={"query": "里程碑", "kb_ids": [kb_id], "top_k": 3}))
    print("rag context len ->", st, len(body.get("context", "")))

asyncio.run(main())
print("DONE")
