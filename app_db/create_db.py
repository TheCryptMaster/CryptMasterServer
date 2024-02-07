import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_HOST = "your_postgres_host"
DB_PORT = "your_postgres_port"
DB_USER = "your_admin_user"
DB_PASSWORD = "your_admin_password"
NEW_USER = "new_user"
NEW_USER_PASSWORD = "your_user_password"
NEW_DB = "new_database"

# Establish a connection to the PostgreSQL server
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database="postgres"  # Connect to the default 'postgres' database for administrative tasks
)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

# Check if the user exists
cursor.execute(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname=%s"), [NEW_USER])
existing_user_check = cursor.fetchone()
if not existing_user_check:
    print(f"Creating user: {NEW_USER}")
    cursor.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(NEW_USER)), [NEW_USER_PASSWORD])
else:
    print(f"User {NEW_USER} already exists.")

# Check if the database exists
cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname=%s"), [NEW_DB])
existing_db_check = cursor.fetchone()
if not existing_db_check:
    print(f"Creating database: {NEW_DB}")
    cursor.execute(sql.SQL("CREATE DATABASE {} WITH OWNER = {}").format(
        sql.Identifier(NEW_DB), sql.Identifier(NEW_USER)
    ))
else:
    print(f"Database {NEW_DB} already exists.")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()