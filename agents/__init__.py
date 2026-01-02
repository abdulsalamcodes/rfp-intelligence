"""
RFP Intelligence - Agents Package

CrewAI agents for RFP analysis, compliance, drafting, and review.
"""

from agents.base import get_llm, get_default_llm, validate_json_output
from agents.rfp_analysis_agent import (
    create_rfp_analysis_agent,
    create_rfp_analysis_task,
    analyze_rfp
)
from agents.compliance_agent import (
    create_compliance_agent,
    create_compliance_task,
    analyze_compliance
)
from agents.technical_drafting_agent import (
    create_technical_drafting_agent,
    create_technical_drafting_task,
    draft_technical_proposal,
    revise_proposal_with_feedback
)
from agents.experience_matching_agent import (
    create_experience_matching_agent,
    create_experience_matching_task,
    match_experience
)
from agents.risk_review_agent import (
    create_risk_review_agent,
    create_risk_review_task,
    review_proposal
)

__all__ = [
    # Base
    "get_llm",
    "get_default_llm",
    "validate_json_output",
    # RFP Analysis
    "create_rfp_analysis_agent",
    "create_rfp_analysis_task",
    "analyze_rfp",
    # Compliance
    "create_compliance_agent",
    "create_compliance_task",
    "analyze_compliance",
    # Technical Drafting
    "create_technical_drafting_agent",
    "create_technical_drafting_task",
    "draft_technical_proposal",
    "revise_proposal_with_feedback",
    # Experience Matching
    "create_experience_matching_agent",
    "create_experience_matching_task",
    "match_experience",
    # Risk Review
    "create_risk_review_agent",
    "create_risk_review_task",
    "review_proposal",
]
