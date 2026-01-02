"""
RFP Analysis Agent

Parses RFP documents and extracts structured requirements, deadlines,
eligibility criteria, and evaluation methodology.
"""

import json
from crewai import Agent, Task

from agents.base import get_default_llm, AGENT_VERBOSE, validate_json_output


RFP_ANALYSIS_SYSTEM_PROMPT = """You are an expert RFP (Request for Proposal) analyst with 20+ years of experience 
in government and enterprise procurement. Your specialty is extracting structured information from 
complex RFP documents with high accuracy.

Your responsibilities:
1. Parse and understand RFP document content thoroughly
2. Extract all requirements (mandatory and optional)
3. Identify key deadlines and dates
4. Understand evaluation criteria and methodology
5. List all mandatory submission documents
6. Identify eligibility criteria for bidders

You are meticulous, thorough, and never miss important details. You assign confidence scores 
to your extractions based on how clearly the information was stated in the document.

IMPORTANT: You must output ONLY valid JSON. No explanatory text before or after the JSON."""


def create_rfp_analysis_agent() -> Agent:
    """Create the RFP Analysis Agent."""
    return Agent(
        role="RFP Analysis Specialist",
        goal="Extract comprehensive, structured information from RFP documents with high accuracy",
        backstory="""You are a senior procurement specialist who has analyzed thousands of RFPs 
across multiple industries. You understand the nuances of government and enterprise procurement 
language and can identify both explicit and implicit requirements. Your analysis forms the 
foundation for successful proposal development.""",
        llm=get_default_llm(),
        verbose=AGENT_VERBOSE,
        allow_delegation=False
    )


def create_rfp_analysis_task(agent: Agent, rfp_text: str, metadata: dict = None) -> Task:
    """
    Create the RFP analysis task.
    
    Args:
        agent: The RFP Analysis Agent
        rfp_text: Full text content of the RFP document
        metadata: Optional metadata (client name, sector, etc.)
    """
    metadata_context = ""
    if metadata:
        metadata_context = f"""
Additional context provided:
- Client/Issuer: {metadata.get('client_name', 'Unknown')}
- Sector: {metadata.get('sector', 'Unknown')}
- Stated Deadline: {metadata.get('submission_deadline', 'Not provided')}
"""

    return Task(
        description=f"""Analyze the following RFP document and extract all relevant information.
{metadata_context}

RFP DOCUMENT TEXT:
---
{rfp_text}
---

Extract and return a JSON object with the following structure:
{{
    "summary": "Brief 2-3 sentence description of what this RFP is seeking",
    "scope_of_work": ["List of main deliverables/scope items"],
    "eligibility_criteria": [
        {{"criterion": "Eligibility requirement text", "confidence": 0.0-1.0}}
    ],
    "deadlines": {{
        "submission": "YYYY-MM-DD or null",
        "questions": "YYYY-MM-DD or null",
        "site_visit": "YYYY-MM-DD or null",
        "contract_start": "YYYY-MM-DD or null"
    }},
    "evaluation_methodology": {{
        "technical_weight": percentage or null,
        "price_weight": percentage or null,
        "experience_weight": percentage or null,
        "other_criteria": {{"criterion_name": weight}}
    }},
    "mandatory_documents": ["List of required submission documents"],
    "requirements": [
        {{
            "id": "REQ-001",
            "text": "Full requirement text",
            "mandatory": true/false,
            "confidence": 0.0-1.0,
            "source_section": "Section reference if identifiable",
            "category": "technical/administrative/legal/financial"
        }}
    ],
    "extraction_warnings": ["Any issues or ambiguities encountered during extraction"]
}}

Rules:
1. Assign unique IDs to each requirement (REQ-001, REQ-002, etc.)
2. Set confidence scores based on clarity: 0.9+ for explicit, 0.7-0.9 for clear implications, <0.7 for inferences
3. Mark requirements as mandatory=true if they use words like "must", "shall", "required"
4. Include all requirements you find, even if numerous
5. If information is not found, use null rather than guessing
6. Add warnings for ambiguous or unclear sections""",
        expected_output="A valid JSON object containing the structured RFP analysis",
        agent=agent
    )


def analyze_rfp(rfp_text: str, metadata: dict = None) -> dict:
    """
    Run RFP analysis on document text.
    
    Args:
        rfp_text: Full text of the RFP document
        metadata: Optional metadata about the RFP
        
    Returns:
        Structured analysis result as dict
    """
    agent = create_rfp_analysis_agent()
    task = create_rfp_analysis_task(agent, rfp_text, metadata)
    
    # Execute the task
    result = agent.execute_task(task)
    
    # Parse and validate output
    required_keys = ["summary", "requirements"]
    return validate_json_output(result, required_keys)
