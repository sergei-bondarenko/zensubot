import os

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
CONNECTION = psycopg2.connect(DATABASE_URL, sslmode="require")


def db_query(line, fetching=True):
    with CONNECTION:
        with CONNECTION.cursor() as cur:
            cur.execute(line)
            if fetching:
                data = cur.fetchall()
                return data
            return None
