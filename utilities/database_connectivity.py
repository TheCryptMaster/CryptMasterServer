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
    engine = create_engine(db_uri)
    try:
        engine.connect()
    except:
        print('Unable to connect to DB.  Trying to create new DB.')
        try:
            import create_db
            engine = create_engine(db_uri)
        except:
            print('DB Error')
            sys.exit()
    try:
        psql.read_sql_query("SELECT * from cm_control", con=engine)
    except:
        print('Empty DB Exists.  Creating new DB.')
        #import prepare_db




test_db_con()