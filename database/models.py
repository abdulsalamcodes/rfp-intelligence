"""
Database Models

SQLAlchemy models for RFP Intelligence with multi-tenancy support.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Index, UniqueConstraint, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================================================
# CORE MODELS: Organizations & Users
# ============================================================================

class Organization(Base):
    """
    Organization (Tenant) model.
    
    All RFPs, subscriptions, and usage are scoped to an organization.
    """
    __tablename__ = "organizations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    rfps: Mapped[List["RFP"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="organization",
        uselist=False
    )


class User(Base):
    """User model with authentication fields."""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    memberships: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    """
    Organization membership with roles.
    
    Roles: owner, admin, member, viewer
    """
    __tablename__ = "organization_members"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
    
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )


# ============================================================================
# RFP MODELS
# ============================================================================

class RFP(Base):
    """RFP document model, scoped to organization."""
    __tablename__ = "rfps"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    submission_deadline: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    text_length: Mapped[Optional[int]] = mapped_column(Integer)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="rfps")
    content: Mapped[Optional["RFPContent"]] = relationship(
        back_populates="rfp",
        uselist=False,
        cascade="all, delete-orphan"
    )
    agent_outputs: Mapped[List["AgentOutput"]] = relationship(
        back_populates="rfp",
        cascade="all, delete-orphan"
    )
    jobs: Mapped[List["AnalysisJob"]] = relationship(
        back_populates="rfp",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_rfps_org", "organization_id"),
        Index("idx_rfps_status", "status"),
    )


class RFPContent(Base):
    """RFP text content and original file storage."""
    __tablename__ = "rfp_content"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    rfp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfps.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    original_file: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    rfp: Mapped["RFP"] = relationship(back_populates="content")


class AgentOutput(Base):
    """Agent output storage with versioning."""
    __tablename__ = "agent_outputs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    rfp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfps.id", ondelete="CASCADE"),
        nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    rfp: Mapped["RFP"] = relationship(back_populates="agent_outputs")
    
    __table_args__ = (
        UniqueConstraint("rfp_id", "agent_name", "version", name="uq_rfp_agent_version"),
        Index("idx_agent_outputs_rfp", "rfp_id"),
    )


class AnalysisJob(Base):
    """Analysis job tracking for persistent status."""
    __tablename__ = "analysis_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    rfp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfps.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="queued")
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=5)
    step_name: Mapped[Optional[str]] = mapped_column(String(100))
    step_description: Mapped[Optional[str]] = mapped_column(Text)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    logs: Mapped[list] = mapped_column(JSONB, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text)
    results_summary: Mapped[Optional[dict]] = mapped_column(JSONB)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    rfp: Mapped["RFP"] = relationship(back_populates="jobs")
    
    __table_args__ = (
        Index("idx_jobs_rfp", "rfp_id"),
        Index("idx_jobs_status", "status"),
    )


class UserEdit(Base):
    """Track user edits to proposal sections."""
    __tablename__ = "user_edits"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    rfp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfps.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    section: Mapped[str] = mapped_column(String(255))
    original_content: Mapped[Optional[str]] = mapped_column(Text)
    edited_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )


# ============================================================================
# BILLING MODELS
# ============================================================================

class Plan(Base):
    """Subscription plan definitions."""
    __tablename__ = "plans"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    price_monthly: Mapped[int] = mapped_column(Integer, default=0)  # in cents
    price_yearly: Mapped[int] = mapped_column(Integer, default=0)  # in cents
    rfp_limit: Mapped[Optional[int]] = mapped_column(Integer)  # NULL = unlimited
    user_limit: Mapped[Optional[int]] = mapped_column(Integer)  # NULL = unlimited
    history_days: Mapped[int] = mapped_column(Integer, default=30)
    features: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lemonsqueezy_variant_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )


class Subscription(Base):
    """Organization subscription status."""
    __tablename__ = "subscriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="active")
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    lemonsqueezy_subscription_id: Mapped[Optional[str]] = mapped_column(String(255))
    lemonsqueezy_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship()


class Usage(Base):
    """Monthly usage tracking per organization."""
    __tablename__ = "usage"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    rfps_used: Mapped[int] = mapped_column(Integer, default=0)
    rfps_limit: Mapped[Optional[int]] = mapped_column(Integer)
    extra_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    __table_args__ = (
        UniqueConstraint("organization_id", "period_start", name="uq_org_period"),
    )


class CreditPurchase(Base):
    """Extra credit purchases."""
    __tablename__ = "credit_purchases"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, nullable=False)  # in cents
    lemonsqueezy_order_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )


class Invoice(Base):
    """Invoice records."""
    __tablename__ = "invoices"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in cents
    status: Mapped[str] = mapped_column(String(50), default="pending")
    lemonsqueezy_invoice_id: Mapped[Optional[str]] = mapped_column(String(255))
    invoice_pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )


class APIKey(Base):
    """API keys for external integrations."""
    __tablename__ = "api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=lambda: ["read", "write"])
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
