from __future__ import annotations

"""Apply a checked-in SQL schema using DATABASE_URL from the project .env."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
ALLOWED_SCHEMAS = {"sec_form4_schema.sql", "analyst_rating_schema.sql"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", choices=sorted(ALLOWED_SCHEMAS))
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    database_url = str(os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    import psycopg
    sql = (PROJECT_ROOT / args.schema).read_text(encoding="utf-8")
    with psycopg.connect(database_url, connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
    print(f"Applied schema: {args.schema}")


if __name__ == "__main__":
    main()
