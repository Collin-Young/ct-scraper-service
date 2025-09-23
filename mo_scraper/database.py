"""MO Database connection and initialization."""
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from .models import Base


DB_PATH = os.getenv('MO_DB_PATH', 'data/mo_cases.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database by creating all tables if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"MO database initialized at {DB_PATH}")
    except SQLAlchemyError as e:
        print(f"Error initializing MO database: {e}")


def get_session():
    """Get a new database session."""
    return SessionLocal()