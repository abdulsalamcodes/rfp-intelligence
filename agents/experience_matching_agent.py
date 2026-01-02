"""
Experience & Personnel Matching Agent

Matches RFP requirements to past projects, staff CVs, and certifications.
Identifies experience gaps that need to be addressed.
"""

import json
from crewai import Agent, Task

from agents.base import get_default_llm, AGENT_VERBOSE, validate_json_output


EXPERIENCE_MATCHING_PROMPT = """You are an expert at matching organizational capabilities to RFP requirements. 
You specialize in:

1. Analyzing past project relevance to new opportunities
2. Identifying the right personnel for proposed roles
3. Finding gaps in experience that need to be addressed
4. Presenting experience in the most compelling way

You understand that evaluators look for relevant, recent experience and qualified personnel.
You focus on demonstrable outcomes and specific qualifications.

IMPORTANT: You must output ONLY valid JSON. No explanatory text before or after the JSON."""


def create_experience_matching_agent() -> Agent:
    """Create the Experience & Personnel Matching Agent."""
    return Agent(
        role="Experience & Personnel Matcher",
        goal="Match company experience and personnel to RFP requirements, identifying gaps",
        backstory="""You are a proposal coordinator who has staffed hundreds of projects. 
You know how to present experience in the best light while remaining truthful. You understand 
that evaluators verify claims, so you focus on genuine matches rather than stretching the truth. 
You're skilled at identifying when teaming partners or subcontractors might be needed.""",
        llm=get_default_llm(),
        verbose=AGENT_VERBOSE,
        allow_delegation=False
    )


def create_experience_matching_task(
    agent: Agent, 
    analysis_result: dict,
    past_projects: list[dict],
    personnel: list[dict]
) -> Task:
    """
    Create the experience matching task.
    
    Args:
        agent: The Experience Matching Agent
        analysis_result: Output from the RFP Analysis Agent
        past_projects: List of past project records
        personnel: List of personnel records
    """
    requirements = analysis_result.get("requirements", [])
    
    # Create a focused requirements list for matching
    requirements_summary = []
    for req in requirements[:20]:  # Limit to avoid token overflow
        requirements_summary.append({
            "id": req.get("id"),
            "text": req.get("text", "")[:200],
            "category": req.get("category")
        })
    
    return Task(
        description=f"""Match company experience and personnel to RFP requirements.

RFP SUMMARY:
{analysis_result.get('summary', 'No summary available')}

KEY REQUIREMENTS TO MATCH:
{json.dumps(requirements_summary, indent=2)}

PAST PROJECTS DATABASE:
{json.dumps(past_projects, indent=2)}

PERSONNEL DATABASE:
{json.dumps(personnel, indent=2)}

Create a JSON response with experience mappings:
{{
    "experience_mapping": [
        {{
            "requirement_id": "REQ-001",
            "requirement_text": "Brief text",
            "matched_projects": [
                {{
                    "project_name": "Project Alpha",
                    "client": "Client Name",
                    "description": "Why this project is relevant",
                    "relevance": 0.0-1.0 score,
                    "year": 2023
                }}
            ],
            "matched_personnel": [
                {{
                    "name": "John Smith",
                    "role": "Proposed role for this project",
                    "current_title": "Current Job Title",
                    "years_experience": 10,
                    "relevant_certifications": ["PMP", "AWS"],
                    "relevance": 0.0-1.0 score
                }}
            ],
            "confidence": 0.0-1.0 overall match confidence
        }}
    ],
    "gaps": [
        {{
            "requirement_id": "REQ-XXX",
            "gap_description": "What experience or capability is missing",
            "severity": "low/medium/high",
            "recommendation": "How to address this gap (training, hiring, teaming)"
        }}
    ],
    "overall_experience_score": 0.0-1.0,
    "personnel_coverage_summary": "Brief summary of staffing readiness"
}}

Matching Guidelines:
- Relevance 0.9+: Direct, highly similar experience
- Relevance 0.7-0.9: Related experience in similar context
- Relevance 0.5-0.7: Transferable skills apply
- Relevance <0.5: Weak match, consider as gap

Only include projects/personnel with relevance 0.5 or higher.
Gaps should be identified for any requirement without a 0.7+ match.""",
        expected_output="A valid JSON object containing experience mappings and gaps",
        agent=agent
    )


def match_experience(
    analysis_result: dict,
    past_projects: list[dict],
    personnel: list[dict]
) -> dict:
    """
    Match experience and personnel to RFP requirements.
    
    Args:
        analysis_result: Output from the RFP Analysis Agent
        past_projects: List of past project records
        personnel: List of personnel records
        
    Returns:
        Experience mapping result as dict
    """
    agent = create_experience_matching_agent()
    task = create_experience_matching_task(agent, analysis_result, past_projects, personnel)
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["experience_mapping", "gaps"]
    return validate_json_output(result, required_keys)
