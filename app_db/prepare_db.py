from sqlalchemy import create_engine, Column, Integer, String, DateTime, MetaData
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Step 3: Create a database engine
database_url = 'sqlite:///example.db'
engine = create_engine(database_url, echo=True)

# Step 4: Define a model
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

# Step 5: Create the table
metadata = MetaData()
Base.metadata.create_all(bind=engine)