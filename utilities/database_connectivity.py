import pandas.io.sql as psql
import sys

from utilities.key_crypt import encrypt_secret
from utilities.secret_generator import get_db_secret, generate_secret
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
    clean_query = sqlalchemy_escape(query)
    engine = create_engine(db_uri, pool_size=10, max_overflow=20)
    with engine.connect() as conn, conn.begin():
        conn.execute(text(clean_query))
    engine.dispose()

def query_db(query):
    engine = create_engine(db_uri)
    response = psql.read_sql_query(query, con=engine)
    engine.dispose()
    return response



def get_version():
    needs_update = False
    version_query = query_db(f"SELECT version_active FROM system_info ORDER BY ID DESC LIMIT 1")
    if len(version_query) == 0:
        needs_update = False
        version = None
    else:
        version = version_query['version_active'][0]
    return needs_update, version


def check_db_con():
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
        psql.read_sql_query("SELECT * from system_info", con=engine)
    except:
        print('Empty DB Exists.  Creating new DB.')
        from utilities.prepare_db import get_clean_sql_schema, get_new_db_statements
        schema_commands = get_clean_sql_schema(LATEST_VERSION)
        for command in schema_commands:
            execute_db(command)
        new_db_commands = get_new_db_statements()
        for command in new_db_commands:
            execute_db(command)
        print(f'DB Schema {LATEST_VERSION} Deployed\n\n')
        set_domain_name()
        set_host_name()
    needs_update, version = get_version()
    if needs_update:
        print('Updating DB')
        # from prepare_db import patch_db
        # patch_db(version)


def sqlalchemy_escape(sql_string):
    fixed_string = sql_string.replace('%', '%%').replace(':', '\:')
    return fixed_string



def set_domain_name():
    fail_count = 0
    while True:
        fail_count += 1
        if fail_count > 3:
            print('Failed to set domain. Please set the domain from setup before using the Crypt Master.')
            break
        domain_name = input('\nWhat domain name will you use with your Crypt Master? i.e. yourdomain.com: ')
        correct = input(f'You entered {domain_name}.  Is that correct?  (y/n): ')
        encrypted_domain = encrypt_secret(generate_secret('domain'), domain_name)
        if correct[:1].lower() == 'y':
            execute_db(f"UPDATE cryptmaster_warden SET domain_name = '{encrypted_domain}'")
            break
    return


def set_host_name():
    fail_count = 0
    while True:
        fail_count += 1
        if fail_count > 3:
            print('Failed to set host name. Please set the host name from setup before using the Crypt Master.')
            break
        host_name = input('\nWhat host name will you use with your Crypt Master? (default: secure-api): ')
        if host_name == '':
            host_name = 'secure-api'
        correct = input(f'You entered {host_name}.  Is that correct?  (y/n): ')
        encrypted_hostname = encrypt_secret(generate_secret('hostname'), host_name)
        if correct[:1].lower() == 'y':
            execute_db(f"UPDATE cryptmaster_warden SET host_name = '{encrypted_hostname}'")
            break
    return



check_db_con()