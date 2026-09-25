from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Field, Relationship, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

DATABASE_URL = "sqlite+aiosqlite:///data/database.db"
engine = create_async_engine(DATABASE_URL, echo=False)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_maker() as session:
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
    location: list[int] | None


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
    location: list[int] | None = Field(default=None, sa_column=Column(JSON))


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
