from sqlmodel import SQLModel, Field, select, Session, create_engine
from typing import Optional

DATABASE_URL = "sqlite:///data/database.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session

class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    time: str
    image: str
    isNew: bool

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    image: str
