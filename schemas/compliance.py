"""
Compliance Schemas

Data models for compliance matrix and risk assessment.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Status of a compliance item."""
    PENDING = "pending"
    MET = "met"
    NOT_MET = "not_met"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(str, Enum):
    """Risk level for flagged items."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceItem(BaseModel):
    """A single item in the compliance matrix."""
    requirement_id: str = Field(..., description="Reference to requirement ID")
    requirement_text: Optional[str] = Field(default=None, description="Requirement text for reference")
    mandatory: bool = Field(default=True, description="Whether mandatory")
    status: ComplianceStatus = Field(
        default=ComplianceStatus.PENDING,
        description="Compliance status"
    )
    response_location: Optional[str] = Field(
        default=None,
        description="Where in proposal this is addressed"
    )
    notes: str = Field(default="", description="Notes or comments")
    evidence: Optional[str] = Field(
        default=None,
        description="Evidence or reference for compliance"
    )


class RiskFlag(BaseModel):
    """A risk identified during compliance review."""
    requirement_id: str = Field(..., description="Related requirement ID")
    risk_level: RiskLevel = Field(..., description="Severity level")
    category: Optional[str] = Field(
        default=None,
        description="Risk category (legal, technical, financial, etc.)"
    )
    explanation: str = Field(..., description="Detailed explanation of the risk")
    mitigation: Optional[str] = Field(
        default=None,
        description="Suggested mitigation strategy"
    )


class ComplianceResult(BaseModel):
    """Complete compliance analysis result."""
    rfp_id: str = Field(..., description="Reference to RFP ID")
    compliance_matrix: list[ComplianceItem] = Field(
        default_factory=list,
        description="Full compliance matrix"
    )
    risk_flags: list[RiskFlag] = Field(
        default_factory=list,
        description="Identified risks"
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Information needed for compliance"
    )
    mandatory_count: int = Field(default=0, description="Total mandatory requirements")
    mandatory_met: int = Field(default=0, description="Mandatory requirements met")
    optional_count: int = Field(default=0, description="Total optional requirements")
    optional_met: int = Field(default=0, description="Optional requirements met")
    overall_compliance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall compliance percentage"
    )
