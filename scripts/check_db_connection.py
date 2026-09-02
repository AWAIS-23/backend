import asyncio
import re
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings


def mask_url(url: str) -> str:
    """Masks password inside a database connection URI."""
    return re.sub(r":([^@/]+)@", r":***@", url)


async def check_connection() -> None:
    settings = get_settings()
    db_url = settings.DATABASE_URL

    masked = mask_url(db_url)
    print(f"Target Database Host: db.ykkaogqgqetamefdjriz.supabase.co:5432")
    print(f"Database Name: postgres")
    print(f"User: postgres")
    print(f"Connection URL format: {masked}")

    if "YOUR_DATABASE_PASSWORD" in db_url or "your-db-password" in db_url:
        print("\nStatus: Ready for database credentials.")
        print("Note: The local .env file has been configured with the exact Supabase host, port, user, and database.")
        print("Set your database password in .env to verify live connection.")
        sys.exit(0)

    try:
        engine = create_async_engine(db_url, connect_args={"connect_timeout": 10})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            row = result.fetchone()
            print("\nSupabase PostgreSQL connection: OK")
            if row:
                print(f"PostgreSQL engine version: {row[0]}")
        await engine.dispose()
    except Exception as exc:
        err_msg = mask_url(str(exc))
        print(f"\nSupabase PostgreSQL connection FAILED: {err_msg}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_connection())
