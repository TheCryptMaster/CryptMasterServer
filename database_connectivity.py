import os
import pandas.io.sql as psql
import sys

from sqlalchemy import create_engine

dev_db_file = '/app_db/dev_db_file.db'
db_file = '/app_db/db_file.db'


if os.path.isfile(f'.{dev_db_file}'):
    db_file = dev_db_file


db_uri = f'sqlite://{db_file}'




def execute_db(query):
    engine = create_engine(db_uri, pool_size=10, max_overflow=20)
    with engine.connect() as conn, conn.begin():
        conn.execute(text(query))
    engine.dispose()

def query_db(query):
    engine = create_engine(db_uri)
    response = psql.read_sql_query(query, con=engine)
    engine.dispose()
    return response


def test_db_con():
    try:
        query_db("SELECT user_name from pa_support_act")
    except:
        print('Unable to connect to database.  Exiting!\n')
        sys.exit()


test_db_con()