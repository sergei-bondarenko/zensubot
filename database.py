import os

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

def db_query(line, fetching=True, sync = False):
    connection = psycopg2.connect(DATABASE_URL, sslmode="require", async = sync)
    with connection:
        with connection.cursor() as cur:
            cur.execute(line)
            if fetching:
                data = cur.fetchall()
                return data
            return None
