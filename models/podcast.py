import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, Index, String, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_uuid()
    )

    notebook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    script: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    audio_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    duration: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    voice: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    source_ids: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    metadata_: Mapped[Optional[str]] = mapped_column(
        "metadata",
        Text,
        nullable=True
    )

    notebook: Mapped["Notebook"] = relationship(
        "Notebook",
        back_populates="podcasts"
    )