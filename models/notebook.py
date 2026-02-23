import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, Enum, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid


class Note(Base):
    """
    笔记表ORM模型
    """
    __tablename__ = "notes"
    # 添加索引以提高查询性能
    __table_args__ = (
        Index('idx_note_create', 'created_at'),
    )

    # 主键 - 使用UUID字符串
    id: Mapped[str] = mapped_column(String(36),  primary_key=True, default=lambda: generate_uuid(), comment="笔记ID")
    notebook_id: Mapped[str] = mapped_column(String(36), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, comment="所属笔记本ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="笔记标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="笔记内容")
    type: Mapped[str] = mapped_column(Text, nullable=False, comment="笔记类型：summary-摘要, faq-问答, study_guide-学习指南, outline-大纲, custom-自定义")
    source_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="关联的源ID列表（JSON数组字符串")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True, comment="元数据（JSON字符串）")
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="notes", lazy="joined")

    # 属性访问器，用于方便地访问metadata
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

    @property
    def source_ids_dict(self) -> Optional[dict]:
        """获取解析后的metadata字典"""
        if self.source_ids is None:
            return {}
        try:
            return json.loads(self.source_ids)
        except (json.JSONDecodeError, TypeError):
            return None

    @source_ids_dict.setter
    def source_ids_dict(self, value: Optional[dict]):
        """设置metadata字典，自动转换为JSON字符串"""
        if value is None:
            self.source_ids = ""
        else:
            self.source_ids = json.dumps(value, ensure_ascii=False)

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}', notebook_id={self.notebook_id})>"


class Notebook(Base):
    """
    笔记本表ORM模型
    """
    __tablename__ = "notebooks"

    # 添加索引以提高查询性能
    __table_args__ = (
        Index('idx_notebook_update', 'updated_at'),
    )

    # 主键 - 使用UUID字符串
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: generate_uuid(), comment="笔记本ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="笔记本名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="笔记本描述")
    is_public: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="是否公开")
    public_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="公开访问令牌")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", Text, default="", comment="元数据（JSON字符串）")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="notebooks", lazy="select")
    sources: Mapped[List["Source"]] = relationship("Source", back_populates="notebook", cascade="all, delete-orphan", lazy="select", order_by="Source.created_at")
    notes: Mapped[List["Note"]] = relationship("Note", back_populates="notebook", cascade="all, delete-orphan", lazy="select", order_by="Note.created_at")
    chat_sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="notebook", cascade="all, delete-orphan", lazy="select", order_by="ChatSession.created_at.desc()")
    podcasts: Mapped[List["Podcast"]] = relationship("Podcast", back_populates="notebook", cascade="all, delete-orphan", lazy="select", order_by="Podcast.created_at")

    def __repr__(self):
        return f"<Notebook(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    # 属性访问器，用于方便地访问metadata
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
