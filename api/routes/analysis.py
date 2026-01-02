"""
Analysis Routes

Endpoints for running RFP analysis and agent workflows.
"""

import json
import logging
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services import get_storage
from crew import RFPCrew

# Set up logger
logger = logging.getLogger("rfp_intelligence.api.analysis")

router = APIRouter()

# Thread pool for running crew tasks
executor = ThreadPoolExecutor(max_workers=2)

# Enhanced job status tracking (use Redis/DB in production)
job_status = {}

# Track job_id by rfp_id for quick lookup
rfp_job_mapping = {}


def create_job_status(job_id: str, rfp_id: str) -> dict:
    """Create a new job status entry."""
    return {
        "job_id": job_id,
        "rfp_id": rfp_id,
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "current_step": 0,
        "total_steps": 5,
        "step_name": None,
        "step_description": "Waiting to start",
        "progress_percent": 0,
        "logs": [],
        "error": None,
        "results_summary": None
    }


def update_job_progress(job_id: str, progress: dict):
    """Callback to update job progress from crew."""
    if job_id in job_status:
        job_status[job_id].update({
            "current_step": progress.get("current_step", 0),
            "step_name": progress.get("step_name"),
            "step_description": progress.get("step_description"),
            "progress_percent": progress.get("progress_percent", 0),
            "status": progress.get("status", "running")
        })
        # Append new logs
        for log in progress.get("logs", []):
            if log not in job_status[job_id]["logs"]:
                job_status[job_id]["logs"].append(log)
        # Keep only last 20 logs
        job_status[job_id]["logs"] = job_status[job_id]["logs"][-20:]


class AnalyzeRequest(BaseModel):
    """Request to analyze an RFP."""
    rfp_id: str
    run_full_workflow: bool = True
    company_context: Optional[dict] = None


class AnalyzeResponse(BaseModel):
    """Response from analysis request."""
    job_id: str
    rfp_id: str
    status: str
    message: str


class AgentRequest(BaseModel):
    """Request to run a specific agent."""
    rfp_id: str
    agent_name: str


def run_crew_workflow(job_id: str, rfp_id: str, company_context: Optional[dict] = None):
    """Background task to run the full crew workflow."""
    storage = get_storage()
    
    try:
        # Update status to running
        job_status[job_id]["status"] = "running"
        job_status[job_id]["started_at"] = datetime.now().isoformat()
        job_status[job_id]["step_description"] = "Loading RFP data"
        
        logger.info(f"[{job_id}] Starting analysis for RFP: {rfp_id}")
        
        # Load RFP text
        text = storage.get_raw_text(rfp_id)
        if not text:
            job_status[job_id]["status"] = "failed"
            job_status[job_id]["error"] = "RFP text not found"
            return
        
        metadata = storage.get_rfp_metadata(rfp_id)
        
        # Load knowledge base
        past_projects = []
        personnel = []
        
        projects_file = storage.data_dir / "knowledge_base" / "past_projects.json"
        if projects_file.exists():
            with open(projects_file) as f:
                past_projects = json.load(f)
        
        personnel_file = storage.data_dir / "knowledge_base" / "personnel.json"
        if personnel_file.exists():
            with open(personnel_file) as f:
                personnel = json.load(f)
        
        # Create progress callback
        def progress_callback(progress: dict):
            update_job_progress(job_id, progress)
        
        # Run crew with progress callback
        crew = RFPCrew(
            rfp_id=rfp_id,
            rfp_text=text,
            metadata=metadata,
            past_projects=past_projects,
            personnel=personnel,
            company_context=company_context,
            progress_callback=progress_callback
        )
        
        results = crew.run_full_workflow()
        
        # Save individual outputs
        if results.get("analysis"):
            storage.save_agent_output(rfp_id, "analysis", results["analysis"])
        if results.get("compliance"):
            storage.save_agent_output(rfp_id, "compliance", results["compliance"])
        if results.get("experience"):
            storage.save_agent_output(rfp_id, "experience", results["experience"])
        if results.get("proposal"):
            storage.save_agent_output(rfp_id, "proposal", results["proposal"])
        if results.get("review"):
            storage.save_agent_output(rfp_id, "review", results["review"])
        
        # Update metadata
        metadata["status"] = "analyzed"
        metadata["analyzed_at"] = datetime.now().isoformat()
        storage.save_rfp_metadata(rfp_id, metadata)
        
        # Update job status
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["completed_at"] = datetime.now().isoformat()
        job_status[job_id]["progress_percent"] = 100
        job_status[job_id]["step_description"] = "Analysis complete"
        job_status[job_id]["results_summary"] = {
            "requirements_count": len(results.get("analysis", {}).get("requirements", [])),
            "compliance_score": results.get("compliance", {}).get("overall_compliance_score"),
            "quality_score": results.get("review", {}).get("overall_quality_score"),
            "recommendation": results.get("review", {}).get("recommendation")
        }
        
        logger.info(f"[{job_id}] Analysis completed successfully for RFP: {rfp_id}")
        
    except Exception as e:
        logger.error(f"[{job_id}] Analysis failed for RFP {rfp_id}: {str(e)}")
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["completed_at"] = datetime.now().isoformat()
        job_status[job_id]["error"] = str(e)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_rfp(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Start RFP analysis workflow.
    
    Runs the full multi-agent workflow in the background.
    Use /api/status/{job_id} to check progress.
    """
    storage = get_storage()
    
    # Verify RFP exists
    metadata = storage.get_rfp_metadata(request.rfp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    text = storage.get_raw_text(request.rfp_id)
    if not text:
        raise HTTPException(status_code=400, detail="RFP text not extracted")
    
    # Generate job ID
    job_id = f"job_{request.rfp_id}_{datetime.now().strftime('%H%M%S')}"
    
    # Create enhanced job status
    job_status[job_id] = create_job_status(job_id, request.rfp_id)
    rfp_job_mapping[request.rfp_id] = job_id
    
    logger.info(f"Starting analysis job {job_id} for RFP: {request.rfp_id}")
    
    # Start background task
    background_tasks.add_task(
        run_crew_workflow,
        job_id,
        request.rfp_id,
        request.company_context
    )
    
    return AnalyzeResponse(
        job_id=job_id,
        rfp_id=request.rfp_id,
        status="queued",
        message="Analysis workflow started. Check /api/status/{job_id} for progress."
    )


@router.post("/analyze/{rfp_id}/rerun")
async def rerun_analysis(rfp_id: str, background_tasks: BackgroundTasks):
    """
    Rerun analysis for an existing RFP.
    
    Useful after editing or to refresh results.
    """
    storage = get_storage()
    
    # Verify RFP exists
    metadata = storage.get_rfp_metadata(rfp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    text = storage.get_raw_text(rfp_id)
    if not text:
        raise HTTPException(status_code=400, detail="RFP text not found")
    
    # Generate new job ID
    job_id = f"job_{rfp_id}_{datetime.now().strftime('%H%M%S')}"
    
    # Create enhanced job status
    job_status[job_id] = create_job_status(job_id, rfp_id)
    rfp_job_mapping[rfp_id] = job_id
    
    logger.info(f"Rerunning analysis job {job_id} for RFP: {rfp_id}")
    
    # Start background task
    background_tasks.add_task(
        run_crew_workflow,
        job_id,
        rfp_id,
        None  # No company context for rerun
    )
    
    return {
        "job_id": job_id,
        "rfp_id": rfp_id,
        "status": "queued",
        "message": "Analysis rerun started. Check /api/status/{job_id} for progress."
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the detailed status of an analysis job."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]


@router.get("/rfp/{rfp_id}/status")
async def get_rfp_analysis_status(rfp_id: str):
    """Get the latest job status for an RFP."""
    if rfp_id not in rfp_job_mapping:
        return {
            "rfp_id": rfp_id,
            "has_job": False,
            "status": "no_analysis",
            "message": "No analysis has been run for this RFP"
        }
    
    job_id = rfp_job_mapping[rfp_id]
    if job_id not in job_status:
        return {
            "rfp_id": rfp_id,
            "has_job": False,
            "status": "no_analysis",
            "message": "Job status not found"
        }
    
    return {
        "rfp_id": rfp_id,
        "has_job": True,
        **job_status[job_id]
    }


@router.get("/results/{rfp_id}")
async def get_results(rfp_id: str):
    """Get all analysis results for an RFP."""
    storage = get_storage()
    
    metadata = storage.get_rfp_metadata(rfp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    outputs = storage.get_all_agent_outputs(rfp_id)
    
    return {
        "rfp_id": rfp_id,
        "metadata": metadata,
        "outputs": outputs
    }


@router.get("/results/{rfp_id}/{agent_name}")
async def get_agent_result(rfp_id: str, agent_name: str):
    """Get specific agent output for an RFP."""
    valid_agents = ["analysis", "compliance", "experience", "proposal", "review"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid agent name. Must be one of: {valid_agents}"
        )
    
    storage = get_storage()
    output = storage.get_agent_output(rfp_id, agent_name)
    
    if not output:
        raise HTTPException(status_code=404, detail=f"No {agent_name} output found")
    
    return output


@router.post("/agents/{agent_name}")
async def run_single_agent(agent_name: str, request: AgentRequest):
    """
    Run a single agent on an RFP.
    
    Useful for re-running specific agents after edits.
    """
    valid_agents = ["analysis", "compliance", "experience", "proposal", "review"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent name. Must be one of: {valid_agents}"
        )
    
    storage = get_storage()
    
    # Verify RFP exists
    text = storage.get_raw_text(request.rfp_id)
    if not text:
        raise HTTPException(status_code=404, detail="RFP text not found")
    
    metadata = storage.get_rfp_metadata(request.rfp_id)
    
    try:
        from agents import (
            analyze_rfp as run_analyze_rfp, 
            analyze_compliance, 
            draft_technical_proposal,
            match_experience, 
            review_proposal
        )
        
        if agent_name == "analysis":
            result = run_analyze_rfp(text, metadata)
        
        elif agent_name == "compliance":
            analysis = storage.get_agent_output(request.rfp_id, "analysis")
            if not analysis:
                raise HTTPException(status_code=400, detail="Run analysis first")
            result = analyze_compliance(analysis)
        
        elif agent_name == "experience":
            analysis = storage.get_agent_output(request.rfp_id, "analysis")
            if not analysis:
                raise HTTPException(status_code=400, detail="Run analysis first")
            result = match_experience(analysis, [], [])
        
        elif agent_name == "proposal":
            analysis = storage.get_agent_output(request.rfp_id, "analysis")
            compliance = storage.get_agent_output(request.rfp_id, "compliance")
            if not analysis or not compliance:
                raise HTTPException(status_code=400, detail="Run analysis and compliance first")
            result = draft_technical_proposal(analysis, compliance)
        
        elif agent_name == "review":
            analysis = storage.get_agent_output(request.rfp_id, "analysis")
            compliance = storage.get_agent_output(request.rfp_id, "compliance")
            proposal = storage.get_agent_output(request.rfp_id, "proposal")
            experience = storage.get_agent_output(request.rfp_id, "experience")
            if not all([analysis, compliance, proposal, experience]):
                raise HTTPException(status_code=400, detail="Run all prior agents first")
            result = review_proposal(analysis, compliance, proposal, experience)
        
        # Save result
        storage.save_agent_output(request.rfp_id, agent_name, result)
        
        return {
            "status": "success",
            "agent": agent_name,
            "rfp_id": request.rfp_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Agent {agent_name} failed for RFP {request.rfp_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
