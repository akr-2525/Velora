from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.db.database import Base


class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    linked_goal_id = Column(
        Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )

    title = Column(String, nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # MODULE 3: commitment_type
    # "planned"     — scheduled in advance; tracked for execution analytics
    # "retroactive" — already done; tracked for time-allocation only
    commitment_type = Column(String, default="planned", nullable=False)

    # MODULE 8: focus_area — tagged from user's configured focus areas
    focus_area = Column(String, nullable=True)

    # confidence only applies to planned commitments
    confidence_level = Column(Integer, nullable=True)

    status = Column(String, default="pending", nullable=False)
    # planned lifecycle:    pending → active → completed | partial | missed
    # retroactive lifecycle: always starts and stays "completed"

    completion_percentage = Column(Integer, default=0, nullable=False)

    # Post-execution note — qualitative context for AI coach
    outcome_note = Column(Text, nullable=True)

    # MODULE 5: structured failure reason
    # "external_blocker" | "underestimated_time" | "distraction_avoidance" | NULL
    failure_reason = Column(String, nullable=True)

    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    reschedule_count = Column(Integer, default=0, nullable=False)

    # procrastination_flag is only set for planned commitments
    # Triggers: reschedule_count >= 2 OR failure_reason == "distraction_avoidance"
    procrastination_flag = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="commitments")
    goal = relationship("Goal", foreign_keys=[linked_goal_id])
