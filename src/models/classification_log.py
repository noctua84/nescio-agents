from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base

if TYPE_CHECKING:
    from src.models.correction import Correction


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    router_decision: Mapped[int] = mapped_column(nullable=False)
    router_method: Mapped[str] = mapped_column(nullable=False)
    confidence_score: Mapped[float] = mapped_column(nullable=False)
    actual_tier_used: Mapped[int] = mapped_column(nullable=True)
    escalated: Mapped[bool] = mapped_column(nullable=False)
    escalated_reason: Mapped[str] = mapped_column(Text, nullable=True)
    user_override: Mapped[bool] = mapped_column(default=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="original_classification",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("router_decision IN (1, 2, 3)", name="ck_router_decision"),
        CheckConstraint("router_method IN ('embedding', 'tiny_llm', 'hybrid')", name="ck_router_method"),
        CheckConstraint("actual_tier_used IN (1, 2, 3)", name="ck_actual_tier_used"),
    )
