"""
RFP Intelligence - Crew Orchestration

Orchestrates the multi-agent workflow for RFP analysis and proposal generation.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path

from config.settings import settings
from agents import (
    analyze_rfp,
    analyze_compliance,
    draft_technical_proposal,
    match_experience,
    review_proposal
)

# Set up logger
logger = logging.getLogger("rfp_intelligence.crew")


# Step definitions for progress tracking
WORKFLOW_STEPS = [
    {"step": 1, "name": "analysis", "description": "Analyzing RFP document"},
    {"step": 2, "name": "compliance", "description": "Creating compliance matrix"},
    {"step": 3, "name": "experience", "description": "Matching past experience"},
    {"step": 4, "name": "proposal", "description": "Drafting proposal sections"},
    {"step": 5, "name": "review", "description": "Quality review and risk assessment"},
]


class RFPCrew:
    """
    Orchestrates the RFP analysis crew workflow.
    
    The workflow executes agents in this order:
    1. RFP Analysis Agent - Extract requirements
    2. Compliance Agent - Create compliance matrix (can run parallel with Experience)
    3. Experience Matching Agent - Match to past projects (can run parallel with Compliance)
    4. Technical Drafting Agent - Draft proposal sections
    5. Risk Review Agent - Quality review
    """
    
    def __init__(
        self,
        rfp_id: str,
        rfp_text: str,
        metadata: Optional[dict] = None,
        past_projects: Optional[list[dict]] = None,
        personnel: Optional[list[dict]] = None,
        company_context: Optional[dict] = None,
        progress_callback: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize the RFP Crew.
        
        Args:
            rfp_id: Unique identifier for this RFP
            rfp_text: Full text of the RFP document
            metadata: Optional RFP metadata (client, sector, deadline)
            past_projects: Optional list of past project records
            personnel: Optional list of personnel records
            company_context: Optional company information
            progress_callback: Optional callback for progress updates
        """
        self.rfp_id = rfp_id
        self.rfp_text = rfp_text
        self.metadata = metadata or {}
        self.past_projects = past_projects or []
        self.personnel = personnel or []
        self.company_context = company_context or {}
        self.progress_callback = progress_callback
        
        # Progress tracking
        self.current_step = 0
        self.total_steps = len(WORKFLOW_STEPS)
        self.logs: list[dict] = []
        
        # Results storage
        self.results = {
            "rfp_id": rfp_id,
            "started_at": None,
            "completed_at": None,
            "status": "pending",
            "analysis": None,
            "compliance": None,
            "experience": None,
            "proposal": None,
            "review": None,
            "errors": []
        }
        
        logger.info(f"Initialized RFPCrew for RFP: {rfp_id}")
    
    def _log(self, message: str, level: str = "info"):
        """Add a log entry and notify callback."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        self.logs.append(log_entry)
        
        # Log to Python logger
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(f"[{self.rfp_id}] {message}")
        
        # Notify callback if provided
        if self.progress_callback:
            self.progress_callback(self._get_progress())
    
    def _get_progress(self) -> dict:
        """Get current progress status."""
        step_info = WORKFLOW_STEPS[self.current_step - 1] if self.current_step > 0 else None
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": step_info["name"] if step_info else None,
            "step_description": step_info["description"] if step_info else "Initializing",
            "progress_percent": int((self.current_step / self.total_steps) * 100) if self.current_step > 0 else 0,
            "status": self.results["status"],
            "logs": self.logs[-10:]  # Last 10 log entries
        }
    
    def _start_step(self, step_num: int):
        """Mark a step as started."""
        self.current_step = step_num
        step = WORKFLOW_STEPS[step_num - 1]
        self._log(f"Step {step_num}/{self.total_steps}: {step['description']}...")
    
    def _complete_step(self, step_num: int, success: bool = True):
        """Mark a step as completed."""
        step = WORKFLOW_STEPS[step_num - 1]
        status = "completed" if success else "failed"
        self._log(f"Step {step_num} ({step['name']}) {status}", "info" if success else "error")

    def _load_knowledge_base(self):
        """Load knowledge base data if not provided."""
        if not self.past_projects:
            projects_file = settings.knowledge_base_dir / "past_projects.json"
            if projects_file.exists():
                with open(projects_file, "r") as f:
                    self.past_projects = json.load(f)
        
        if not self.personnel:
            personnel_file = settings.knowledge_base_dir / "personnel.json"
            if personnel_file.exists():
                with open(personnel_file, "r") as f:
                    self.personnel = json.load(f)
    
    def _save_results(self):
        """Save results to disk."""
        output_file = settings.outputs_dir / f"{self.rfp_id}_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
    
    def run_analysis(self) -> dict:
        """Run the RFP Analysis Agent only."""
        try:
            self.results["analysis"] = analyze_rfp(self.rfp_text, self.metadata)
            return self.results["analysis"]
        except Exception as e:
            self.results["errors"].append(f"Analysis failed: {str(e)}")
            raise
    
    def run_compliance(self, analysis_result: Optional[dict] = None) -> dict:
        """Run the Compliance Agent."""
        analysis = analysis_result or self.results.get("analysis")
        if not analysis:
            raise ValueError("Analysis result required. Run analysis first.")
        
        try:
            self.results["compliance"] = analyze_compliance(analysis)
            return self.results["compliance"]
        except Exception as e:
            self.results["errors"].append(f"Compliance analysis failed: {str(e)}")
            raise
    
    def run_experience_matching(self, analysis_result: Optional[dict] = None) -> dict:
        """Run the Experience Matching Agent."""
        analysis = analysis_result or self.results.get("analysis")
        if not analysis:
            raise ValueError("Analysis result required. Run analysis first.")
        
        self._load_knowledge_base()
        
        try:
            self.results["experience"] = match_experience(
                analysis, 
                self.past_projects, 
                self.personnel
            )
            return self.results["experience"]
        except Exception as e:
            self.results["errors"].append(f"Experience matching failed: {str(e)}")
            raise
    
    def run_drafting(
        self, 
        analysis_result: Optional[dict] = None,
        compliance_result: Optional[dict] = None
    ) -> dict:
        """Run the Technical Drafting Agent."""
        analysis = analysis_result or self.results.get("analysis")
        compliance = compliance_result or self.results.get("compliance")
        
        if not analysis:
            raise ValueError("Analysis result required. Run analysis first.")
        if not compliance:
            raise ValueError("Compliance result required. Run compliance first.")
        
        try:
            self.results["proposal"] = draft_technical_proposal(
                analysis,
                compliance,
                self.company_context
            )
            return self.results["proposal"]
        except Exception as e:
            self.results["errors"].append(f"Proposal drafting failed: {str(e)}")
            raise
    
    def run_review(
        self,
        analysis_result: Optional[dict] = None,
        compliance_result: Optional[dict] = None,
        proposal_result: Optional[dict] = None,
        experience_result: Optional[dict] = None
    ) -> dict:
        """Run the Risk Review Agent."""
        analysis = analysis_result or self.results.get("analysis")
        compliance = compliance_result or self.results.get("compliance")
        proposal = proposal_result or self.results.get("proposal")
        experience = experience_result or self.results.get("experience")
        
        if not all([analysis, compliance, proposal, experience]):
            raise ValueError("All prior results required. Run full workflow first.")
        
        try:
            self.results["review"] = review_proposal(
                analysis,
                compliance,
                proposal,
                experience
            )
            return self.results["review"]
        except Exception as e:
            self.results["errors"].append(f"Review failed: {str(e)}")
            raise
    
    def run_full_workflow(self) -> dict:
        """
        Run the complete RFP analysis and proposal workflow.
        
        Returns:
            Complete results dict with all agent outputs
        """
        self.results["started_at"] = datetime.now().isoformat()
        self.results["status"] = "running"
        self._log("Starting full RFP analysis workflow")
        
        try:
            # Step 1: RFP Analysis
            self._start_step(1)
            self.run_analysis()
            self._complete_step(1)
            
            # Step 2: Compliance Analysis
            self._start_step(2)
            self.run_compliance()
            self._complete_step(2)
            
            # Step 3: Experience Matching
            self._start_step(3)
            self.run_experience_matching()
            self._complete_step(3)
            
            # Step 4: Technical Drafting
            self._start_step(4)
            self.run_drafting()
            self._complete_step(4)
            
            # Step 5: Quality Review
            self._start_step(5)
            self.run_review()
            self._complete_step(5)
            
            self.results["status"] = "completed"
            self.results["completed_at"] = datetime.now().isoformat()
            self._log("Workflow completed successfully!", "info")
            
        except Exception as e:
            self.results["status"] = "failed"
            self.results["completed_at"] = datetime.now().isoformat()
            self._log(f"Workflow failed: {str(e)}", "error")
            raise
        
        finally:
            self._save_results()
        
        return self.results


def run_rfp_workflow(
    rfp_id: str,
    rfp_text: str,
    metadata: Optional[dict] = None,
    **kwargs
) -> dict:
    """
    Convenience function to run the full RFP workflow.
    
    Args:
        rfp_id: Unique RFP identifier
        rfp_text: Full RFP document text
        metadata: Optional metadata
        **kwargs: Additional arguments for RFPCrew
        
    Returns:
        Complete workflow results
    """
    crew = RFPCrew(rfp_id, rfp_text, metadata, **kwargs)
    return crew.run_full_workflow()
