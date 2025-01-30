from sqlmodel import create_engine, Session
from typing import Generator

sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, echo=True)

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session