import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, Index, String, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid


class Source(Base):
    __tablename__ = "sources"

    # 添加索引以提高查询性能
    __table_args__ = (
        Index('idx_source_create', 'created_at'),
        Index('idx_file_name', 'file_name')
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: generate_uuid())
    notebook_id: Mapped[str] = mapped_column(String(36), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="sources")

    @property
    def metadata_dict(self) -> Optional[dict]:
        """获取解析后的metadata字典"""
        if self.metadata_ is None:
            return {}
        try:
            return json.loads(self.metadata_)
        except (json.JSONDecodeError, TypeError):
            return None

    @metadata_dict.setter
    def metadata_dict(self, value: Optional[dict]):
        """设置metadata字典，自动转换为JSON字符串"""
        if value is None:
            self.metadata_ = ""
        else:
            self.metadata_ = json.dumps(value, ensure_ascii=False)
