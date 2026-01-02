"""
Compliance Agent

Converts extracted requirements into a compliance matrix, flags mandatory vs optional items,
identifies missing information and high-risk clauses.
"""

import json
from crewai import Agent, Task

from agents.base import get_default_llm, AGENT_VERBOSE, validate_json_output


COMPLIANCE_SYSTEM_PROMPT = """You are a compliance and risk assessment specialist with deep expertise 
in government contracting and proposal compliance. Your role is to:

1. Create comprehensive compliance matrices
2. Identify mandatory vs optional requirements
3. Flag high-risk clauses and terms
4. Identify missing or unclear information
5. Assess the risk of non-compliance

You think systematically and ensure nothing falls through the cracks. You understand that 
compliance failures lead to disqualification, so you are thorough and conservative in your assessments.

IMPORTANT: You must output ONLY valid JSON. No explanatory text before or after the JSON."""


def create_compliance_agent() -> Agent:
    """Create the Compliance Agent."""
    return Agent(
        role="Compliance & Risk Specialist",
        goal="Create comprehensive compliance matrices and identify risks in RFP requirements",
        backstory="""You are a former government contracting officer who now helps companies 
respond to RFPs. You've seen thousands of proposals disqualified for compliance failures, 
so you are meticulous about ensuring every requirement is tracked and addressed. You have 
a keen eye for risky contract terms and hidden obligations.""",
        llm=get_default_llm(),
        verbose=AGENT_VERBOSE,
        allow_delegation=False
    )


def create_compliance_task(agent: Agent, analysis_result: dict) -> Task:
    """
    Create the compliance analysis task.
    
    Args:
        agent: The Compliance Agent
        analysis_result: Output from the RFP Analysis Agent
    """
    requirements_json = json.dumps(analysis_result.get("requirements", []), indent=2)
    
    return Task(
        description=f"""Based on the RFP analysis results, create a comprehensive compliance matrix 
and risk assessment.

RFP SUMMARY:
{analysis_result.get('summary', 'No summary available')}

MANDATORY DOCUMENTS REQUIRED:
{json.dumps(analysis_result.get('mandatory_documents', []), indent=2)}

EXTRACTED REQUIREMENTS:
{requirements_json}

Create a JSON response with the following structure:
{{
    "compliance_matrix": [
        {{
            "requirement_id": "REQ-001",
            "requirement_text": "Brief text for reference",
            "mandatory": true/false,
            "status": "pending",
            "response_location": null,
            "notes": "Any notes about addressing this requirement",
            "evidence": null
        }}
    ],
    "risk_flags": [
        {{
            "requirement_id": "REQ-XXX",
            "risk_level": "low/medium/high/critical",
            "category": "legal/technical/financial/schedule/resource",
            "explanation": "Why this poses a risk",
            "mitigation": "Suggested mitigation strategy"
        }}
    ],
    "missing_information": [
        "List of clarifications or information needed to properly respond"
    ],
    "mandatory_count": total number of mandatory requirements,
    "optional_count": total number of optional requirements,
    "high_risk_count": number of high/critical risk items
}}

Flagging Guidelines:
- CRITICAL risk: Could lead to contract termination, legal liability, or major financial loss
- HIGH risk: Difficult to comply with, tight deadlines, unusual liability terms
- MEDIUM risk: Challenging but manageable with proper planning
- LOW risk: Standard requirements with minor complexity

Look for these risk indicators:
- Unlimited liability clauses
- Unrealistic timelines
- Vague scope that could expand
- Penalty clauses
- Insurance requirements above industry standards
- Intellectual property concerns
- Exclusive dealing requirements""",
        expected_output="A valid JSON object containing the compliance matrix and risk assessment",
        agent=agent
    )


def analyze_compliance(analysis_result: dict) -> dict:
    """
    Run compliance analysis on RFP analysis results.
    
    Args:
        analysis_result: Output from the RFP Analysis Agent
        
    Returns:
        Compliance matrix and risk assessment as dict
    """
    agent = create_compliance_agent()
    task = create_compliance_task(agent, analysis_result)
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["compliance_matrix", "risk_flags"]
    return validate_json_output(result, required_keys)
