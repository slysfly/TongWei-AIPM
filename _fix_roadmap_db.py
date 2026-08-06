import asyncio
from app.db.session import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        # Add missing updated_at column
        try:
            await conn.execute(text("ALTER TABLE roadmap_items ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            print("OK: added updated_at column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("OK: updated_at already exists")
            else:
                print(f"ERR adding updated_at: {e}")

        # Verify
        r = await conn.execute(text("PRAGMA table_info(roadmap_items)"))
        cols = [row[1] for row in r.fetchall()]
        print(f"Total columns: {len(cols)}")
        print(f"Has updated_at: {'updated_at' in cols}")

if __name__ == "__main__":
    asyncio.run(main())
