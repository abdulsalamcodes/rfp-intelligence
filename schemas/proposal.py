"""
Proposal Schemas

Data models for proposal drafting, experience matching, and review.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProposalSection(BaseModel):
    """A section of the proposal draft."""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content/draft")
    order: int = Field(default=0, description="Section order in proposal")
    source_references: list[str] = Field(
        default_factory=list,
        description="RFP sections referenced"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made in this section"
    )
    word_count: int = Field(default=0, description="Word count")
    status: str = Field(default="draft", description="Section status")


class ProposalDraft(BaseModel):
    """Complete proposal draft."""
    rfp_id: str = Field(..., description="Reference to RFP ID")
    sections: list[ProposalSection] = Field(
        default_factory=list,
        description="Proposal sections"
    )
    total_word_count: int = Field(default=0, description="Total word count")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ExperienceMatch(BaseModel):
    """A matched past project for a requirement."""
    project_name: str = Field(..., description="Project name")
    client: Optional[str] = Field(default=None, description="Client name")
    description: str = Field(default="", description="Project description")
    relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score"
    )
    year: Optional[int] = Field(default=None, description="Project year")


class PersonnelMatch(BaseModel):
    """A matched personnel for a requirement."""
    name: str = Field(..., description="Personnel name")
    role: str = Field(..., description="Proposed role")
    current_title: Optional[str] = Field(default=None, description="Current job title")
    years_experience: Optional[int] = Field(default=None, description="Years of experience")
    relevant_certifications: list[str] = Field(
        default_factory=list,
        description="Relevant certifications"
    )
    relevance: float = Field(default=0.0, description="Relevance score")


class ExperienceMapping(BaseModel):
    """Experience mapping for a single requirement."""
    requirement_id: str = Field(..., description="Requirement ID")
    requirement_text: Optional[str] = Field(default=None, description="Requirement text")
    matched_projects: list[ExperienceMatch] = Field(
        default_factory=list,
        description="Matched past projects"
    )
    matched_personnel: list[PersonnelMatch] = Field(
        default_factory=list,
        description="Matched personnel"
    )
    confidence: float = Field(default=0.0, description="Overall match confidence")


class ExperienceGap(BaseModel):
    """An identified gap in experience."""
    requirement_id: str = Field(..., description="Requirement ID")
    gap_description: str = Field(..., description="Description of the gap")
    severity: str = Field(default="medium", description="Gap severity")
    recommendation: Optional[str] = Field(
        default=None,
        description="Recommendation to address gap"
    )


class ExperienceResult(BaseModel):
    """Complete experience matching result."""
    rfp_id: str = Field(..., description="Reference to RFP ID")
    experience_mapping: list[ExperienceMapping] = Field(
        default_factory=list,
        description="Experience mappings per requirement"
    )
    gaps: list[ExperienceGap] = Field(
        default_factory=list,
        description="Identified experience gaps"
    )
    overall_experience_score: float = Field(
        default=0.0,
        description="Overall experience match score"
    )


class IssueType(str, Enum):
    """Types of issues found during review."""
    AMBIGUITY = "ambiguity"
    OVERCONFIDENCE = "overconfidence"
    MISSING_JUSTIFICATION = "missing_justification"
    INCONSISTENCY = "inconsistency"
    INCOMPLETE = "incomplete"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    GRAMMAR = "grammar"


class ReviewItem(BaseModel):
    """A single review finding."""
    section: str = Field(..., description="Section where issue was found")
    issue_type: IssueType = Field(..., description="Type of issue")
    severity: str = Field(default="medium", description="Issue severity")
    description: str = Field(..., description="Issue description")
    location: Optional[str] = Field(
        default=None,
        description="Specific location in section"
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Suggested fix"
    )


class ReviewResult(BaseModel):
    """Complete review result."""
    rfp_id: str = Field(..., description="Reference to RFP ID")
    review_items: list[ReviewItem] = Field(
        default_factory=list,
        description="Review findings"
    )
    overall_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall quality score"
    )
    critical_issues_count: int = Field(
        default=0,
        description="Number of critical issues"
    )
    recommendation: str = Field(
        default="",
        description="Overall recommendation"
    )
