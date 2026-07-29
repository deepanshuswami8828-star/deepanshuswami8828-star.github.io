import os
from sqlmodel import create_engine, Session, SQLModel

raw_db_url = os.getenv("DATABASE_URL")

if raw_db_url and raw_db_url.strip():
    db_url = raw_db_url.strip()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
else:
    # Fallback to local SQLite if DATABASE_URL is unset
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtestlab.db")
    db_url = f"sqlite:///{sqlite_path}"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, connect_args=connect_args, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
