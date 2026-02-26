from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, Index, String, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid


class ChatMessage(Base):
    """
    聊天消息表ORM模型
    """
    __tablename__ = "chat_messages"

    # 添加索引以提高查询性能
    __table_args__ = (
        # 角色的索引，用于按角色筛选消息
        # 创建时间的索引，用于获取最新消息
        Index('idx_chat_message_created', 'created_at'),
    )

    # 主键 - 使用UUID字符串
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_uuid(),
        comment="消息ID"
    )

    # 外键 - 指向聊天会话表
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),  # 会话删除时消息也删除
        nullable=False,
        comment="所属会话ID"
    )

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息角色：user-用户, assistant-助手, system-系统"
    )

    # 消息内容
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容"
    )

    # 关联的源ID列表（JSON字符串）
    sources: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="关联的源ID列表（JSON数组字符串）"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )

    # JSON元数据字段
    metadata_: Mapped[Optional[str]] = mapped_column(
        "metadata",
        Text,
        nullable=True,
        comment="元数据（JSON字符串）"
    )

    # 关系定义
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
        lazy="joined"  # 通常查询消息时会需要会话信息
    )


class ChatSession(Base):
    """
    聊天会话表ORM模型
    """
    __tablename__ = "chat_sessions"

    # 添加索引以提高查询性能
    __table_args__ = (
        # 笔记本ID和创建时间的组合索引，常用于按时间顺序查看会话
        Index('idx_chatsession_updated_at', 'updated_at'),

        # 标题索引，用于搜索
        Index('idx_chatsession_title', 'title'),
    )

    # 主键 - 使用UUID字符串
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_uuid(),
        comment="聊天会话ID"
    )

    # 外键 - 指向笔记本表
    notebook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notebooks.id", ondelete="CASCADE"),  # 笔记本删除时会话也会被删除
        nullable=False,
        comment="所属笔记本ID"
    )

    # 基本字段
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="会话标题"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,  # 更新时自动设置
        nullable=False,
        comment="更新时间"
    )

    # JSON元数据字段
    metadata_: Mapped[Optional[str]] = mapped_column(
        "metadata",
        Text,
        nullable=True,
        comment="元数据（JSON字符串）"
    )

    # 关系定义
    notebook: Mapped["Notebook"] = relationship(
        "Notebook",
        back_populates="chat_sessions",
        lazy="joined"  # 通常查询会话时会需要笔记本信息
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",            # 会话删除时，消息也删除
        lazy="selectin",
        order_by="ChatMessage.created_at.asc()"  # 按创建时间升序排序
    )
