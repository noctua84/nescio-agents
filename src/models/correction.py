from datetime import timezone, datetime

from sqlalchemy import ForeignKey, CheckConstraint, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_classification_id: Mapped[int] = mapped_column(ForeignKey("classification_logs.id", ondelete="CASCADE"), nullable=False)
    corrected_tier: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_type: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(tz=timezone.utc))

    __table_args__ = (
        CheckConstraint("corrected_tier IN (1, 2, 3)", name='ck_corrected_tier'),
        CheckConstraint("feedback_type IN ('escalation', 'user_override', 'latency')", name='ck_feedback_type'),
    )