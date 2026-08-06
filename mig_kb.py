import asyncio
from app.db.session import engine
from sqlalchemy import text
async def mig():
    async with engine.connect() as conn:
        await conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'private'"))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_kb_visibility ON knowledge_bases(visibility)'))
        await conn.commit()
        print('OK')
asyncio.run(mig())
