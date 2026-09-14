from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///data/database.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


class AlertRead(SQLModel):
    id: int | None = None
    title: str
    time: str
    date: str
    image: str
    isNew: bool
    recognised_user_id: int | None
    embedding: list[float] | None
    confidence: float = Field(default=0.0)


class FaceTemplateRead(SQLModel):
    id: int
    filepath: str
    user_id: int


class UserRead(SQLModel):
    id: int
    name: str
    images: list[FaceTemplateRead] = []
    alerts: list[AlertRead] = []
    is_trusted: bool
    is_temporary: bool


class Alert(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    image: str
    time: str
    date: str
    isNew: bool = Field(default=True)
    recognised_user_id: int | None = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="alerts")
    embedding: list[float] | None = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    confidence: float = Field(default=0.0)


class FaceTemplate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    filepath: str
    embedding: list[float] = Field(sa_column=Column(JSON))
    user: "User" = Relationship(back_populates="images")


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    images: list["FaceTemplate"] = Relationship(back_populates="user")
    alerts: list["Alert"] = Relationship(back_populates="user")
    is_trusted: bool = Field(default=False)
    is_temporary: bool = Field(default=True)
