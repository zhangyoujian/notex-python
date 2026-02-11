import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_uuid()
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )

    resource_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="activity_logs"
    )