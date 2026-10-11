from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Text, DateTime, Index, CheckConstraint
from sqlalchemy.orm import mapped_column, Mapped

from src.models import Base


class ReferenceLibrary(Base):
    __tablename__ = "reference_library"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    tier: Mapped[int] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(tz=timezone.utc))

    __table_args__ = (
        Index("ix_reference_library_created_at", created_at),
        CheckConstraint("tier IN (1, 2, 3)", name="ck_tier"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_confidence"),
        CheckConstraint("source IN ('curated', 'learned', 'user_override')", name="ck_source"),
    )