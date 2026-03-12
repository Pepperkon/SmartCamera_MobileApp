from sqlmodel import SQLModel, Field, select, Session, create_engine, Relationship
from typing import Optional, List

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

class FaceTemplateRead(SQLModel):
    id: int
    filepath: str
    user_id: int

class UserRead(SQLModel):
    id: int
    name: str
    images: List[FaceTemplateRead] = []

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    images: List["FaceTemplate"] = Relationship(back_populates="user")

class FaceTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    filepath: str
    # embedding: str TODO
    user: User = Relationship(back_populates="images")
