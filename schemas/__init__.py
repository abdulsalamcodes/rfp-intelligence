"""
RFP Intelligence - Pydantic Schemas

Data models for RFP analysis, compliance, and proposals.
"""

from schemas.rfp import (
    RFPMetadata,
    Requirement,
    Deadline,
    EvaluationMethodology,
    RFPAnalysisResult,
)
from schemas.compliance import (
    ComplianceItem,
    RiskFlag,
    ComplianceResult,
)
from schemas.proposal import (
    ProposalSection,
    ExperienceMatch,
    PersonnelMatch,
    ExperienceMapping,
    ExperienceResult,
    ReviewItem,
    ReviewResult,
)

__all__ = [
    # RFP
    "RFPMetadata",
    "Requirement",
    "Deadline",
    "EvaluationMethodology",
    "RFPAnalysisResult",
    # Compliance
    "ComplianceItem",
    "RiskFlag",
    "ComplianceResult",
    # Proposal
    "ProposalSection",
    "ExperienceMatch",
    "PersonnelMatch",
    "ExperienceMapping",
    "ExperienceResult",
    "ReviewItem",
    "ReviewResult",
]
