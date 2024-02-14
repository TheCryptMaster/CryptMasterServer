from getpass import getpass
from psycopg2 import connect, sql
from secret_generator import get_db_secret


# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = 'initial_db_user'
DB_PASSWORD = getpass('Enter initial db secret: ')
DB_NAME = 'initial_db_user_db'

# Establish a connection to the PostgreSQL server



# Create a cursor object to execute SQL queries
def check_user_exists():
    conn = connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    # Check if the user exists
    cursor.execute(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname='cryptmaster'"))
    existing_user_check = cursor.fetchone()
    if not existing_user_check:
        print(f"Creating user: 'cryptmaster'")
        cursor.execute(sql.SQL(f"CREATE USER cryptmaster PASSWORD '{get_db_secret()}'"))
    else:
        print(f"User 'cryptmaster' already exists.")
    conn.commit()
    cursor.close()
    conn.close()
    return


def check_db_exists():
    conn = connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    # Check if the database exists
    cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname='cryptmaster_db'"))
    existing_db_check = cursor.fetchone()
    if not existing_db_check:
        print(f"Creating database: 'cryptmaster_db'")
        cursor.execute(sql.SQL("CREATE DATABASE cryptmaster_db WITH OWNER = cryptmaster"))
    else:
        print(f"Database 'cryptmaster_db' already exists.")
    conn.commit()
    cursor.close()
    conn.close()
    return True

def db_cleanup():
    conn = connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute(sql.SQL("DROP DATABASE IF EXISTS initial_db_user_db"))
    conn.commit()
    cursor.execute(sql.SQL("DROP USER IF EXISTS initial_db_user"))
    conn.commit()
    cursor.close()
    conn.close()
    return


def db_check():
    check_user_exists()
    check_db_exists()
    db_cleanup()
    return


db_check()