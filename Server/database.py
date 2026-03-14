from sqlmodel import SQLModel, Field, select, Session, create_engine, Relationship
from typing import Optional, List

DATABASE_URL = "sqlite:///data/database.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session


class AlertRead(SQLModel):
    id: Optional[int]
    title: str
    time: str
    image: str
    isNew: bool
    captured_user_id: Optional[int]

class FaceTemplateRead(SQLModel):
    id: int
    filepath: str
    user_id: int

class UserRead(SQLModel):
    id: int
    name: str
    images: List[FaceTemplateRead] = []
    alerts: List[AlertRead] = []

class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    image: str
    time: str
    isNew: bool = Field(default=True)
    recognised_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="alerts")

class FaceTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    filepath: str
    # embedding: str TODO
    user: "User" = Relationship(back_populates="images")

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    images: List["FaceTemplate"] = Relationship(back_populates="user")
    alerts: List["Alert"] = Relationship(back_populates="user")
