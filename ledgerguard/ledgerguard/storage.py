"""Small SQLAlchemy-backed snapshot store (SQLite locally, PostgreSQL in deployments)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class RunSnapshot(Base):
    __tablename__ = "release_run_snapshots"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SnapshotStore:
    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("DATABASE_URL", "sqlite:///./ledgerguard.db")
        options = {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        self.engine = create_engine(self.url, connect_args=options, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def load(self, run_id: str) -> dict | None:
        with self.sessions() as session:
            row = session.get(RunSnapshot, run_id)
            return json.loads(row.payload) if row else None

    def save(self, run_id: str, payload: dict) -> None:
        serialized = json.dumps(payload, separators=(",", ":"))
        with self.sessions.begin() as session:
            row = session.get(RunSnapshot, run_id)
            if row:
                row.payload = serialized
                row.updated_at = datetime.now(timezone.utc)
            else:
                session.add(RunSnapshot(run_id=run_id, payload=serialized, updated_at=datetime.now(timezone.utc)))
