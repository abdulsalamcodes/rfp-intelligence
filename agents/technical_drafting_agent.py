"""
Technical Proposal Drafting Agent

Drafts technical approach, methodology, and execution plan sections
based on RFP requirements and available knowledge.
"""

import json
from crewai import Agent, Task

from agents.base import get_default_llm, AGENT_VERBOSE, validate_json_output


TECHNICAL_DRAFTING_PROMPT = """You are an expert technical proposal writer with extensive experience 
in winning competitive bids. You specialize in:

1. Translating requirements into clear technical approaches
2. Developing credible methodologies
3. Creating realistic execution plans
4. Writing persuasive proposal content

You write in a professional, confident tone that demonstrates capability without overcommitting.
You always cite your sources and clearly mark any assumptions.

CRITICAL RULES:
- Never make claims that cannot be supported
- Always mark assumptions explicitly
- Reference the specific RFP sections you are addressing
- Be specific rather than generic
- Focus on the "how" not just the "what"

IMPORTANT: You must output ONLY valid JSON. No explanatory text before or after the JSON."""


def create_technical_drafting_agent() -> Agent:
    """Create the Technical Proposal Drafting Agent."""
    return Agent(
        role="Technical Proposal Writer",
        goal="Draft compelling, technically accurate proposal sections that address RFP requirements",
        backstory="""You are a senior technical writer who has helped win billions of dollars 
in contracts. You understand that evaluators read dozens of proposals, so you make yours 
stand out through clarity, specificity, and demonstrated understanding of the client's needs. 
You never make unsupported claims and always back up your approach with reasoning.""",
        llm=get_default_llm(),
        verbose=AGENT_VERBOSE,
        allow_delegation=False
    )


def create_technical_drafting_task(
    agent: Agent, 
    analysis_result: dict, 
    compliance_result: dict,
    company_context: dict = None
) -> Task:
    """
    Create the technical drafting task.
    
    Args:
        agent: The Technical Drafting Agent
        analysis_result: Output from the RFP Analysis Agent
        compliance_result: Output from the Compliance Agent
        company_context: Optional context about the bidding company
    """
    requirements_json = json.dumps(analysis_result.get("requirements", []), indent=2)
    scope_json = json.dumps(analysis_result.get("scope_of_work", []), indent=2)
    
    company_info = ""
    if company_context:
        company_info = f"""
COMPANY CONTEXT:
- Company Name: {company_context.get('name', 'Our Company')}
- Industry Focus: {company_context.get('focus', 'Professional Services')}
- Key Capabilities: {json.dumps(company_context.get('capabilities', []))}
"""

    return Task(
        description=f"""Draft technical proposal sections based on the RFP analysis.

RFP SUMMARY:
{analysis_result.get('summary', 'No summary available')}

SCOPE OF WORK:
{scope_json}

KEY REQUIREMENTS:
{requirements_json}
{company_info}

Create proposal sections that address the requirements. Return a JSON object:
{{
    "sections": [
        {{
            "title": "Technical Approach",
            "content": "Detailed section content (500-1000 words per section)",
            "order": 1,
            "source_references": ["REQ-001", "REQ-002", "Section 3.1"],
            "assumptions": ["List any assumptions made"]
        }},
        {{
            "title": "Methodology",
            "content": "Detailed methodology content",
            "order": 2,
            "source_references": [],
            "assumptions": []
        }},
        {{
            "title": "Work Plan & Schedule",
            "content": "Execution plan content",
            "order": 3,
            "source_references": [],
            "assumptions": []
        }},
        {{
            "title": "Quality Assurance",
            "content": "QA approach content",
            "order": 4,
            "source_references": [],
            "assumptions": []
        }},
        {{
            "title": "Risk Management",
            "content": "Risk management approach",
            "order": 5,
            "source_references": [],
            "assumptions": []
        }}
    ],
    "overall_approach_summary": "2-3 sentence executive summary of the approach"
}}

Writing Guidelines:
1. Be specific to this RFP, not generic boilerplate
2. Address each major requirement explicitly
3. Use active voice and confident language
4. Include measurable outcomes where possible
5. Reference specific RFP sections/requirements you're addressing
6. Mark ALL assumptions clearly - evaluators hate hidden assumptions
7. Keep each section focused and well-organized
8. Use bullet points for key items, prose for explanations""",
        expected_output="A valid JSON object containing proposal sections",
        agent=agent
    )


def draft_technical_proposal(
    analysis_result: dict, 
    compliance_result: dict,
    company_context: dict = None
) -> dict:
    """
    Draft technical proposal sections.
    
    Args:
        analysis_result: Output from the RFP Analysis Agent
        compliance_result: Output from the Compliance Agent
        company_context: Optional context about the bidding company
        
    Returns:
        Draft sections as dict
    """
    agent = create_technical_drafting_agent()
    task = create_technical_drafting_task(agent, analysis_result, compliance_result, company_context)
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["sections"]
    return validate_json_output(result, required_keys)


def create_proposal_revision_task(
    agent: Agent,
    original_proposal: dict,
    review_feedback: dict,
    analysis_result: dict
) -> Task:
    """
    Create a task to revise the proposal based on review feedback.
    
    Args:
        agent: The Technical Drafting Agent
        original_proposal: The original proposal draft
        review_feedback: Output from the Risk Review Agent
        analysis_result: Output from the RFP Analysis Agent (for context)
    """
    # Format review items by section
    review_items_by_section = {}
    for item in review_feedback.get("review_items", []):
        section = item.get("section", "General")
        if section not in review_items_by_section:
            review_items_by_section[section] = []
        review_items_by_section[section].append({
            "issue_type": item.get("issue_type"),
            "severity": item.get("severity"),
            "description": item.get("description"),
            "suggested_fix": item.get("suggested_fix")
        })
    
    # Format original sections
    original_sections_json = json.dumps(original_proposal.get("sections", []), indent=2)
    review_by_section_json = json.dumps(review_items_by_section, indent=2)
    priority_fixes = review_feedback.get("priority_fixes", [])
    cross_section_issues = review_feedback.get("cross_section_issues", [])
    
    return Task(
        description=f"""Revise and improve the proposal based on quality review feedback.

RFP SUMMARY:
{analysis_result.get('summary', 'No summary available')}

ORIGINAL PROPOSAL SECTIONS:
{original_sections_json}

REVIEW FEEDBACK BY SECTION:
{review_by_section_json}

PRIORITY FIXES (address these first):
{json.dumps(priority_fixes, indent=2)}

CROSS-SECTION ISSUES TO RESOLVE:
{json.dumps(cross_section_issues, indent=2)}

OVERALL REVIEW SCORE: {review_feedback.get('overall_quality_score', 'N/A')}
RECOMMENDATION: {review_feedback.get('recommendation', 'N/A')}

Your task is to REVISE the proposal sections to address the review feedback. Return an improved JSON object:
{{
    "sections": [
        {{
            "title": "Section Title",
            "content": "REVISED content addressing the feedback (500-1000 words per section)",
            "order": 1,
            "source_references": ["REQ-001", "REQ-002"],
            "assumptions": ["Updated assumptions if any"],
            "revisions_made": ["List of specific changes made in this section"]
        }}
    ],
    "overall_approach_summary": "Updated 2-3 sentence executive summary",
    "revision_summary": "Overall summary of major changes made to address the review feedback"
}}

REVISION GUIDELINES:
1. ADDRESS ALL CRITICAL AND HIGH SEVERITY ISSUES - these must be fixed
2. Fix ambiguous statements by being more specific
3. Add evidence or qualifications to overconfident claims
4. Add justifications for "we will do X" statements
5. Resolve any inconsistencies between sections
6. Fill in incomplete coverage of important topics
7. Improve clarity and grammar where flagged
8. Maintain the good aspects highlighted in the review
9. Keep the same section structure unless the feedback specifically requires restructuring
10. Document what you changed in the "revisions_made" field for each section""",
        expected_output="A valid JSON object containing revised proposal sections with documented changes",
        agent=agent
    )


def revise_proposal_with_feedback(
    original_proposal: dict,
    review_feedback: dict,
    analysis_result: dict,
    company_context: dict = None
) -> dict:
    """
    Revise a proposal based on review feedback.
    
    This function takes an existing proposal draft and the feedback from
    the review agent, then generates an improved version that addresses
    the identified issues.
    
    Args:
        original_proposal: The original proposal draft from Technical Drafting Agent
        review_feedback: The review output from Risk Review Agent
        analysis_result: Output from the RFP Analysis Agent (for context)
        company_context: Optional context about the bidding company
        
    Returns:
        Revised proposal sections as dict
    """
    agent = create_technical_drafting_agent()
    task = create_proposal_revision_task(
        agent, 
        original_proposal, 
        review_feedback, 
        analysis_result
    )
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["sections"]
    return validate_json_output(result, required_keys)

