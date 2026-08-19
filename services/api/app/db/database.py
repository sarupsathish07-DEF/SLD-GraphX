from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_PATH = Path("var/db/sldgraphx_m1.sqlite3")
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def initialize_database() -> None:
    from services.api.app.db import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
