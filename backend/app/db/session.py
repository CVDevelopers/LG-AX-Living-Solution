"""Engine/session factory. On Vercel (profile W) the seed DB is a read-only bundle (§12.1)."""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from .. import config


def make_engine(path: str | Path = None, read_only: bool | None = None):
    path = Path(path or config.DB_PATH)
    read_only = config.IS_VERCEL if read_only is None else read_only
    if read_only:

        def connect():
            return sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)

        return create_engine("sqlite://", creator=connect)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def make_session_factory(path: str | Path = None) -> sessionmaker[OrmSession]:
    return sessionmaker(bind=make_engine(path), expire_on_commit=False)
