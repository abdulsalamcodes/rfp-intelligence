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
