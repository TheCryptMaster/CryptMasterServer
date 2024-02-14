import os
import pandas.io.sql as psql
import sys

from utilities.secret_generator import get_db_secret
from sqlalchemy import create_engine, text



# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = 'cryptmaster'
DB_PASSWORD = get_db_secret()
DB_NAME = 'cryptmaster_db'

db_uri = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

LATEST_VERSION = '2.0.0'

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



def get_version():
    needs_update, version = False
    version_file = '.version'
    if not os.path.isfile(version_file):
        version = '0.0.1'
        with open(version_file, 'w+') as f:
            f.write(version)
    with open(version_file, 'r') as f:
        version = f.readline()
    if version != LATEST_VERSION:
        needs_update = True
    return needs_update, version


def test_db_con():
    engine = create_engine(db_uri)
    try:
        engine.connect()
    except:
        print('Unable to connect to DB.  Trying to create new DB.')
        try:
            import utilities.create_db
            engine = create_engine(db_uri)
        except:
            print('DB Error')
            sys.exit()
    try:
        psql.read_sql_query("SELECT * from cm_control", con=engine)
    except:
        print('Empty DB Exists.  Creating new DB.')
        # from prepare_db import fresh_db
        # fresh_db()
    needs_update, version = get_version()
    if needs_update:
        print('Updating DB')
        # from prepare_db import patch_db
        # patch_db(version)





test_db_con()