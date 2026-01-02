"""
Risk & Quality Review Agent

Reviews all generated proposal content for quality, consistency, and issues.
Identifies ambiguity, over-confidence, missing justifications, and inconsistencies.
"""

import json
from crewai import Agent, Task

from agents.base import get_default_llm, AGENT_VERBOSE, validate_json_output


RISK_REVIEW_PROMPT = """You are an expert proposal reviewer and quality assurance specialist. 
Your role is to:

1. Review proposal content for quality and accuracy
2. Identify ambiguous or unclear statements
3. Flag over-confident claims without evidence
4. Find missing justifications or support
5. Detect inconsistencies across sections
6. Ensure compliance claims are accurate

You are skeptical but fair. You provide actionable feedback, not just criticism.
Your goal is to improve the proposal, not tear it down.

IMPORTANT: You must output ONLY valid JSON. No explanatory text before or after the JSON."""


def create_risk_review_agent() -> Agent:
    """Create the Risk & Quality Review Agent."""
    return Agent(
        role="Proposal Quality Reviewer",
        goal="Review proposal content for quality issues and provide actionable improvements",
        backstory="""You are a former proposal evaluator who now helps teams improve their 
submissions. You know exactly what evaluators look for and what red flags they catch. 
You've seen proposals fail due to small inconsistencies and unsupported claims. 
Your reviews are thorough but constructive, focusing on fixes rather than just problems.""",
        llm=get_default_llm(),
        verbose=AGENT_VERBOSE,
        allow_delegation=False
    )


def create_risk_review_task(
    agent: Agent,
    analysis_result: dict,
    compliance_result: dict,
    proposal_draft: dict,
    experience_result: dict
) -> Task:
    """
    Create the quality review task.
    
    Args:
        agent: The Risk Review Agent
        analysis_result: Output from the RFP Analysis Agent
        compliance_result: Output from the Compliance Agent
        proposal_draft: Output from the Technical Drafting Agent
        experience_result: Output from the Experience Matching Agent
    """
    # Summarize proposal sections
    sections_summary = []
    for section in proposal_draft.get("sections", []):
        sections_summary.append({
            "title": section.get("title"),
            "content_preview": section.get("content", "")[:500] + "...",
            "assumptions": section.get("assumptions", []),
            "source_references": section.get("source_references", [])
        })
    
    return Task(
        description=f"""Review the proposal content for quality, accuracy, and consistency.

RFP SUMMARY:
{analysis_result.get('summary', 'No summary available')}

REQUIREMENTS COUNT: {len(analysis_result.get('requirements', []))}

COMPLIANCE STATUS:
- Mandatory Requirements: {compliance_result.get('mandatory_count', 'Unknown')}
- High Risk Items: {compliance_result.get('high_risk_count', 'Unknown')}
- Missing Information: {json.dumps(compliance_result.get('missing_information', []))}

EXPERIENCE GAPS:
{json.dumps([g.get('gap_description', '') for g in experience_result.get('gaps', [])], indent=2)}

PROPOSAL SECTIONS TO REVIEW:
{json.dumps(sections_summary, indent=2)}

Perform a thorough review and return a JSON response:
{{
    "review_items": [
        {{
            "section": "Section title",
            "issue_type": "ambiguity/overconfidence/missing_justification/inconsistency/incomplete/unsupported_claim/grammar",
            "severity": "low/medium/high/critical",
            "description": "What the issue is",
            "location": "Specific quote or reference if available",
            "suggested_fix": "How to fix this issue"
        }}
    ],
    "cross_section_issues": [
        {{
            "sections_involved": ["Section A", "Section B"],
            "issue": "Description of inconsistency between sections",
            "suggested_resolution": "How to resolve"
        }}
    ],
    "compliance_concerns": [
        "Any compliance issues found in the content"
    ],
    "strengths": [
        "What the proposal does well"
    ],
    "overall_quality_score": 0.0-1.0,
    "critical_issues_count": number,
    "recommendation": "ready_with_minor_edits / needs_revision / needs_major_revision",
    "priority_fixes": [
        "Top 3-5 issues to fix first"
    ]
}}

Review Criteria:
1. AMBIGUITY: Vague statements that could be interpreted multiple ways
2. OVERCONFIDENCE: Claims made without evidence or qualification
3. MISSING JUSTIFICATION: "We will do X" without explaining how/why
4. INCONSISTENCY: Conflicting information across sections
5. INCOMPLETE: Important topics not adequately covered
6. UNSUPPORTED CLAIMS: Statements that require evidence but have none
7. GRAMMAR/CLARITY: Writing quality issues

Be specific with issues - vague feedback is not helpful.""",
        expected_output="A valid JSON object containing the quality review results",
        agent=agent
    )


def review_proposal(
    analysis_result: dict,
    compliance_result: dict,
    proposal_draft: dict,
    experience_result: dict
) -> dict:
    """
    Review proposal content for quality issues.
    
    Args:
        analysis_result: Output from the RFP Analysis Agent
        compliance_result: Output from the Compliance Agent
        proposal_draft: Output from the Technical Drafting Agent
        experience_result: Output from the Experience Matching Agent
        
    Returns:
        Review result as dict
    """
    agent = create_risk_review_agent()
    task = create_risk_review_task(
        agent, 
        analysis_result, 
        compliance_result, 
        proposal_draft, 
        experience_result
    )
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["review_items", "overall_quality_score", "recommendation"]
    return validate_json_output(result, required_keys)
