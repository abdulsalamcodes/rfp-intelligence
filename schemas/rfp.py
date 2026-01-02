"""
RFP Analysis Schemas

Data models for RFP document analysis and requirement extraction.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """A single requirement extracted from the RFP."""
    id: str = Field(..., description="Unique requirement identifier (e.g., REQ-001)")
    text: str = Field(..., description="Full requirement text")
    mandatory: bool = Field(default=True, description="Whether this is a mandatory requirement")
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score for extraction accuracy"
    )
    source_section: Optional[str] = Field(
        default=None,
        description="Source section in the RFP document"
    )
    category: Optional[str] = Field(
        default=None,
        description="Requirement category (technical, administrative, etc.)"
    )


class Deadline(BaseModel):
    """Deadline information from the RFP."""
    submission: Optional[date] = Field(default=None, description="Proposal submission deadline")
    questions: Optional[date] = Field(default=None, description="Deadline for questions")
    site_visit: Optional[date] = Field(default=None, description="Site visit date if applicable")
    contract_start: Optional[date] = Field(default=None, description="Expected contract start date")


class EvaluationMethodology(BaseModel):
    """Evaluation criteria and weighting."""
    technical_weight: Optional[float] = Field(default=None, description="Technical score weight (%)")
    price_weight: Optional[float] = Field(default=None, description="Price score weight (%)")
    experience_weight: Optional[float] = Field(default=None, description="Experience score weight (%)")
    other_criteria: Optional[dict[str, float]] = Field(
        default=None,
        description="Other evaluation criteria and weights"
    )


class EligibilityCriterion(BaseModel):
    """An eligibility criterion for bidders."""
    criterion: str = Field(..., description="Eligibility requirement")
    confidence: float = Field(default=0.9, description="Extraction confidence")


class RFPAnalysisResult(BaseModel):
    """Complete result from RFP analysis."""
    summary: str = Field(..., description="Brief description of the RFP")
    scope_of_work: list[str] = Field(default_factory=list, description="Scope items")
    eligibility_criteria: list[EligibilityCriterion] = Field(
        default_factory=list,
        description="Bidder eligibility requirements"
    )
    deadlines: Deadline = Field(default_factory=Deadline, description="Key deadlines")
    evaluation_methodology: Optional[EvaluationMethodology] = Field(
        default=None,
        description="Evaluation criteria"
    )
    mandatory_documents: list[str] = Field(
        default_factory=list,
        description="Required submission documents"
    )
    requirements: list[Requirement] = Field(
        default_factory=list,
        description="Extracted requirements"
    )
    raw_text_length: int = Field(default=0, description="Length of source document text")
    extraction_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings during extraction"
    )


class RFPMetadata(BaseModel):
    """Metadata about an uploaded RFP."""
    id: str = Field(..., description="Unique RFP identifier")
    filename: str = Field(..., description="Original filename")
    client_name: Optional[str] = Field(default=None, description="Client/issuer name")
    sector: Optional[str] = Field(default=None, description="Industry sector")
    submission_deadline: Optional[date] = Field(default=None, description="Submission deadline")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO format)")
    status: str = Field(default="uploaded", description="Processing status")
    text_extracted: bool = Field(default=False, description="Whether text was extracted")
    ocr_used: bool = Field(default=False, description="Whether OCR was needed")
