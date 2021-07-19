import os
from datetime import datetime, timedelta

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


def clean_data(job):
    def cleaner(context):
        db_query(
            """delete from plus_data where date_part('day', now() - created) > 1;
                delete from jobs_updates where job_id in (select id from jobs where type = 0);
                delete from jobs where type = 0;""", False
        )

    job.run_repeating(
        callback=cleaner, interval=timedelta(days=2), first=datetime(2021, 1, 1)
    )
