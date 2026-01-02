"""
Analysis Worker

Background job for running RFP analysis workflow.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from arq import ArqRedis

logger = logging.getLogger("rfp_intelligence.workers.analysis")


async def run_analysis_job(
    ctx: dict,
    job_id: str,
    rfp_id: str,
    org_id: Optional[str] = None
):
    """
    Background job to run the full RFP analysis workflow.
    
    This job:
    1. Updates job status in database
    2. Runs the CrewAI workflow (5 agents)
    3. Saves results to database
    4. Updates final job status
    
    Args:
        ctx: ARQ context with Redis connection
        job_id: Unique job identifier
        rfp_id: RFP to analyze
        org_id: Organization context (for multi-tenancy)
    """
    redis: ArqRedis = ctx["redis"]
    
    # Helper to update status in Redis (fast lookup)
    async def update_status(
        status: str,
        step: int = 0,
        step_name: str = "",
        step_description: str = "",
        progress: int = 0,
        error: Optional[str] = None
    ):
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "status": status,
                "current_step": str(step),
                "step_name": step_name,
                "step_description": step_description,
                "progress_percent": str(progress),
                "error": error or "",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        # Expire job status after 24 hours
        await redis.expire(f"job:{job_id}", 86400)
    
    try:
        logger.info(f"Starting analysis job {job_id} for RFP {rfp_id}")
        
        # Initialize job status
        await update_status(
            status="running",
            step=0,
            step_name="Initializing",
            step_description="Loading RFP document...",
            progress=0
        )
        
        # Import here to avoid circular imports
        from services import get_storage
        from crew import RFPCrew
        
        storage = get_storage()
        
        # Get RFP text
        text = storage.get_raw_text(rfp_id)
        if not text:
            await update_status(status="failed", error="RFP text not found")
            return {"status": "failed", "error": "RFP text not found"}
        
        metadata = storage.get_rfp_metadata(rfp_id) or {}
        
        # Step 1: RFP Analysis Agent
        await update_status(
            status="running",
            step=1,
            step_name="RFP Analysis",
            step_description="Extracting requirements and analyzing document structure...",
            progress=10
        )
        
        # Initialize crew and run
        crew = RFPCrew(storage)
        
        # Create a callback to update progress
        async def progress_callback(step: int, name: str, description: str, progress: int):
            await update_status(
                status="running",
                step=step,
                step_name=name,
                step_description=description,
                progress=progress
            )
        
        # Run the full workflow
        # Note: RFPCrew.run() is synchronous, but we're in async context
        # We'll run it in a thread pool to avoid blocking
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def run_crew_sync():
            return crew.run(rfp_id, text, metadata)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Update progress at intervals
            step_info = [
                (1, "RFP Analysis", "Extracting requirements...", 15),
                (2, "Compliance Check", "Analyzing compliance requirements...", 30),
                (3, "Experience Matching", "Finding relevant past projects...", 50),
                (4, "Proposal Drafting", "Generating proposal sections...", 70),
                (5, "Quality Review", "Reviewing proposal quality...", 90),
            ]
            
            # Start the crew run in background
            future = executor.submit(run_crew_sync)
            
            # Wait for completion, updating status periodically
            while not future.done():
                await asyncio.sleep(5)  # Check every 5 seconds
            
            result = future.result()
        
        # Job completed successfully
        await update_status(
            status="completed",
            step=5,
            step_name="Complete",
            step_description="Analysis completed successfully",
            progress=100
        )
        
        # Update RFP status in storage
        if metadata:
            metadata["status"] = "analyzed"
            storage.save_rfp_metadata(rfp_id, metadata)
        
        logger.info(f"Analysis job {job_id} completed for RFP {rfp_id}")
        
        return {
            "status": "completed",
            "rfp_id": rfp_id,
            "job_id": job_id
        }
        
    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {str(e)}")
        await update_status(
            status="failed",
            error=str(e)
        )
        return {
            "status": "failed",
            "error": str(e)
        }


async def run_single_agent_job(
    ctx: dict,
    job_id: str,
    rfp_id: str,
    agent_name: str,
    org_id: Optional[str] = None
):
    """
    Background job to run a single agent.
    
    Useful for re-running specific agents after manual edits.
    
    Args:
        ctx: ARQ context
        job_id: Unique job identifier
        rfp_id: RFP to process
        agent_name: Which agent to run (analysis, compliance, experience, proposal, review)
        org_id: Organization context
    """
    redis: ArqRedis = ctx["redis"]
    
    try:
        logger.info(f"Running single agent job: {agent_name} for RFP {rfp_id}")
        
        # Update status
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "running",
                "agent": agent_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        await redis.expire(f"job:{job_id}", 86400)
        
        # Import and run agent
        from services import get_storage
        from agents import (
            analyze_rfp,
            analyze_compliance,
            draft_technical_proposal,
            match_experience,
            review_proposal
        )
        
        storage = get_storage()
        
        # Get required data based on agent
        if agent_name == "analysis":
            text = storage.get_raw_text(rfp_id)
            metadata = storage.get_rfp_metadata(rfp_id)
            result = analyze_rfp(text, metadata)
            
        elif agent_name == "compliance":
            analysis = storage.get_agent_output(rfp_id, "analysis")
            if not analysis:
                raise ValueError("Run analysis first")
            result = analyze_compliance(analysis)
            
        elif agent_name == "experience":
            analysis = storage.get_agent_output(rfp_id, "analysis")
            if not analysis:
                raise ValueError("Run analysis first")
            result = match_experience(analysis, [], [])
            
        elif agent_name == "proposal":
            analysis = storage.get_agent_output(rfp_id, "analysis")
            compliance = storage.get_agent_output(rfp_id, "compliance")
            if not analysis or not compliance:
                raise ValueError("Run analysis and compliance first")
            result = draft_technical_proposal(analysis, compliance)
            
        elif agent_name == "review":
            analysis = storage.get_agent_output(rfp_id, "analysis")
            compliance = storage.get_agent_output(rfp_id, "compliance")
            proposal = storage.get_agent_output(rfp_id, "proposal")
            experience = storage.get_agent_output(rfp_id, "experience")
            if not all([analysis, compliance, proposal, experience]):
                raise ValueError("Run all prior agents first")
            result = review_proposal(analysis, compliance, proposal, experience)
            
        else:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        # Save result
        storage.save_agent_output(rfp_id, agent_name, result)
        
        # Update status
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"Single agent job completed: {agent_name} for RFP {rfp_id}")
        
        return {"status": "completed", "agent": agent_name, "rfp_id": rfp_id}
        
    except Exception as e:
        logger.error(f"Single agent job failed: {str(e)}")
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        return {"status": "failed", "error": str(e)}
