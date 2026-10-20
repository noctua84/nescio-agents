from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base

if TYPE_CHECKING:
    from src.models.classification_log import ClassificationLog


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    original_classification_id: Mapped[int] = mapped_column(
        ForeignKey("classification_logs.id", ondelete="CASCADE"), nullable=False, init=False
    )
    corrected_tier: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_type: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), init=False)

    original_classification: Mapped["ClassificationLog"] = relationship(back_populates="corrections")

    __table_args__ = (
        CheckConstraint("corrected_tier IN (1, 2, 3)", name="ck_corrected_tier"),
        CheckConstraint("feedback_type IN ('escalation', 'user_override', 'latency')", name="ck_feedback_type"),
    )
