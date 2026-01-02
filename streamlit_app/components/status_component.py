"""
Status Component - Reusable Analysis Status Display

Displays real-time analysis progress with auto-refresh capability.
"""

import streamlit as st
import httpx
import time
from typing import Optional

API_BASE = "http://localhost:8000"


def get_job_status(job_id: str) -> Optional[dict]:
    """Fetch job status from API."""
    try:
        response = httpx.get(f"{API_BASE}/api/status/{job_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching status: {e}")
    return None


def get_rfp_status(rfp_id: str) -> Optional[dict]:
    """Fetch latest job status for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/rfp/{rfp_id}/status", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching RFP status: {e}")
    return None


def trigger_rerun(rfp_id: str) -> Optional[dict]:
    """Trigger analysis rerun for an RFP."""
    try:
        response = httpx.post(f"{API_BASE}/api/analyze/{rfp_id}/rerun", timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error triggering rerun: {e}")
    return None


def display_analysis_status(
    job_id: Optional[str] = None, 
    rfp_id: Optional[str] = None,
    auto_refresh: bool = True,
    show_rerun_button: bool = False
) -> Optional[dict]:
    """
    Display analysis status with progress bar and logs.
    
    Args:
        job_id: Specific job ID to track
        rfp_id: RFP ID to get latest status for
        auto_refresh: Whether to auto-refresh when running
        show_rerun_button: Whether to show the rerun button
    
    Returns:
        Latest status dict if available
    """
    # Get status
    if job_id:
        status = get_job_status(job_id)
    elif rfp_id:
        status = get_rfp_status(rfp_id)
    else:
        st.warning("No job ID or RFP ID provided")
        return None
    
    if not status:
        st.info("No analysis status available")
        return None
    
    # Check if this is a "no job" response
    if status.get("has_job") is False:
        st.info("📋 No analysis has been run for this RFP yet.")
        if show_rerun_button and rfp_id:
            if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
                result = trigger_rerun(rfp_id)
                if result:
                    st.success("Analysis started!")
                    st.session_state["current_job_id"] = result.get("job_id")
                    st.rerun()
        return None
    
    current_status = status.get("status", "unknown")
    
    # Status header
    col1, col2 = st.columns([3, 1])
    with col1:
        status_icons = {
            "queued": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌"
        }
        icon = status_icons.get(current_status, "❓")
        st.markdown(f"### {icon} Analysis Status: {current_status.title()}")
    
    with col2:
        if current_status == "completed" and show_rerun_button and rfp_id:
            if st.button("🔄 Rerun", use_container_width=True):
                result = trigger_rerun(rfp_id)
                if result:
                    st.success("Rerun started!")
                    st.session_state["current_job_id"] = result.get("job_id")
                    st.rerun()
    
    # Progress bar
    progress = status.get("progress_percent", 0)
    st.progress(progress / 100, text=status.get("step_description", "Processing..."))
    
    # Step details
    if current_status == "running":
        current_step = status.get("current_step", 0)
        total_steps = status.get("total_steps", 5)
        step_name = status.get("step_name", "")
        
        st.caption(f"Step {current_step}/{total_steps}: {step_name}")
    
    # Show logs in expander
    logs = status.get("logs", [])
    if logs:
        with st.expander("📜 Activity Log", expanded=(current_status == "running")):
            for log in reversed(logs[-10:]):  # Show last 10, newest first
                timestamp = log.get("timestamp", "")[:19].replace("T", " ")
                level = log.get("level", "info")
                message = log.get("message", "")
                
                level_icons = {
                    "info": "ℹ️",
                    "error": "❌",
                    "warning": "⚠️"
                }
                icon = level_icons.get(level, "•")
                
                st.caption(f"{icon} [{timestamp}] {message}")
    
    # Error display
    if current_status == "failed":
        error = status.get("error", "Unknown error")
        st.error(f"**Error:** {error}")
        
        if show_rerun_button and rfp_id:
            if st.button("🔄 Retry Analysis", type="primary", use_container_width=True):
                result = trigger_rerun(rfp_id)
                if result:
                    st.success("Retry started!")
                    st.session_state["current_job_id"] = result.get("job_id")
                    st.rerun()
    
    # Results summary for completed
    if current_status == "completed":
        results = status.get("results_summary")
        if results:
            st.markdown("---")
            st.markdown("#### 📊 Results Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Requirements", results.get("requirements_count", "N/A"))
            with col2:
                score = results.get("compliance_score")
                st.metric("Compliance Score", f"{score:.0f}%" if score else "N/A")
            with col3:
                quality = results.get("quality_score")
                st.metric("Quality Score", f"{quality:.0f}%" if quality else "N/A")
    
    # Auto-refresh for running jobs
    if auto_refresh and current_status in ["queued", "running"]:
        time.sleep(2)  # Wait 2 seconds
        st.rerun()
    
    return status


def display_compact_status(rfp_id: str) -> str:
    """
    Display a compact inline status for an RFP.
    
    Returns the current status string.
    """
    status = get_rfp_status(rfp_id)
    
    if not status or status.get("has_job") is False:
        return "not_started"
    
    current_status = status.get("status", "unknown")
    progress = status.get("progress_percent", 0)
    
    status_displays = {
        "queued": "⏳ Queued",
        "running": f"🔄 Running ({progress}%)",
        "completed": "✅ Completed",
        "failed": "❌ Failed"
    }
    
    display = status_displays.get(current_status, f"❓ {current_status}")
    st.caption(display)
    
    return current_status
