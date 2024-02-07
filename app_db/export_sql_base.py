from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base

# Step 1: Create a database engine
database_url = 'sqlite:///existing_database.db'
engine = create_engine(database_url, echo=True)

# Step 2: Reflect the database using automap
Base = automap_base()
Base.prepare(engine, reflect=True)

# Step 3: Access the classes generated from the existing database
# For example, if you have a table named 'users' in the database:
User = Base.classes.users

# Now you can use the User class to query the existing database