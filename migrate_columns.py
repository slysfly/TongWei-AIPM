#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产库列对齐脚本（零数据风险）：
遍历模型中所有表，对「数据库中已存在但缺少某些列」的表，用 ALTER TABLE ADD COLUMN
补齐缺失列。不删除、不修改已有列与数据。运行前请先备份数据库。
"""
import os
import sqlalchemy as sa
from sqlalchemy import inspect, create_engine, text
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

from app.config import settings
from app.db.session import Base
import app.models  # 确保全部模型注册

DB_URL = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine = create_engine(DB_URL, future=True)
d = sqlite_dialect()

added = []
skipped = []

with engine.begin() as conn:
    insp = inspect(engine)
    for tname, table in Base.metadata.tables.items():
        if tname not in insp.get_table_names():
            continue
        exist_cols = {r[1] for r in conn.execute(text(f"PRAGMA table_info({tname})")).fetchall()}
        row_count = conn.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar() or 0
        for col in table.columns:
            if col.name in exist_cols:
                continue
            # 构造类型
            try:
                typ = col.type.compile(dialect=d)
            except Exception:
                typ = "TEXT"
            ddl = f'ALTER TABLE {tname} ADD COLUMN {col.name} {typ}'
            # 默认值的处理（仅使用服务端默认或简单标量默认）
            default_sql = None
            if col.server_default is not None:
                val = getattr(col.server_default, "arg", None)
                if isinstance(val, str):
                    default_sql = val
            elif col.default is not None and not callable(col.default.arg):
                v = col.default.arg
                if isinstance(v, (int, float, bool, str)):
                    default_sql = repr(v) if isinstance(v, str) else str(v)
            if default_sql:
                ddl += f" DEFAULT {default_sql}"
            if not col.nullable and default_sql is None and row_count > 0:
                skipped.append(f"{tname}.{col.name} (NOT NULL 无默认值且表非空，跳过)")
                continue
            try:
                conn.execute(text(ddl))
                added.append(f"{tname}.{col.name} ({typ})")
                print("ADD:", ddl)
            except Exception as e:
                skipped.append(f"{tname}.{col.name}: {e}")

print("\n===== 补齐完成 =====")
print(f"已添加列数: {len(added)}")
for a in added:
    print("  +", a)
if skipped:
    print(f"\n跳过 {len(skipped)} 项:")
    for s in skipped:
        print("  -", s)
