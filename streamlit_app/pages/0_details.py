"""
RFP Details Page - View Uploaded RFP Information

Displays comprehensive details about an uploaded RFP including:
- Document metadata
- Extracted text preview
- Analysis status and results summary
- Navigation to analysis pages
"""

import streamlit as st
import httpx
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="RFP Details", page_icon="📋", layout="wide")

API_BASE = "http://localhost:8000"


def get_rfps():
    """Get list of RFPs."""
    try:
        response = httpx.get(f"{API_BASE}/api/documents/", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []


def get_rfp_details(rfp_id: str):
    """Get full RFP metadata."""
    try:
        response = httpx.get(f"{API_BASE}/api/documents/{rfp_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_rfp_text(rfp_id: str):
    """Get extracted RFP text."""
    try:
        response = httpx.get(f"{API_BASE}/api/documents/{rfp_id}/text", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_analysis_results(rfp_id: str):
    """Get all analysis results for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/results/{rfp_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_analysis_status(rfp_id: str):
    """Get current analysis job status for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/rfp/{rfp_id}/status", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def trigger_analysis(rfp_id: str):
    """Trigger a new analysis for the RFP."""
    try:
        response = httpx.post(
            f"{API_BASE}/api/analyze",
            json={"rfp_id": rfp_id, "run_full_workflow": True},
            timeout=30
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.text
    except Exception as e:
        return None, str(e)


def rerun_analysis(rfp_id: str):
    """Rerun analysis for the RFP."""
    try:
        response = httpx.post(
            f"{API_BASE}/api/analyze/{rfp_id}/rerun",
            timeout=30
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.text
    except Exception as e:
        return None, str(e)


def format_datetime(iso_str: str) -> str:
    """Format ISO datetime string for display."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except:
        return iso_str


def main():
    st.title("📋 RFP Details")
    st.markdown("View comprehensive details about your uploaded RFP documents.")
    
    # Get list of RFPs for selection
    rfps = get_rfps()
    
    if not rfps:
        st.warning("No RFPs found. Please upload an RFP first.")
        if st.button("📤 Go to Upload", type="primary"):
            st.switch_page("pages/1_upload.py")
        return
    
    # Check if we have a pre-selected RFP from session state
    current_rfp_id = st.session_state.get("current_rfp_id")
    
    # Build RFP selection options
    rfp_options = {f"{r['filename']} ({r['rfp_id']})": r['rfp_id'] for r in rfps}
    rfp_ids = list(rfp_options.values())
    
    # Find default index
    default_index = 0
    if current_rfp_id and current_rfp_id in rfp_ids:
        default_index = rfp_ids.index(current_rfp_id)
    
    # RFP selector
    selected = st.selectbox(
        "Select RFP",
        options=list(rfp_options.keys()),
        index=default_index
    )
    
    rfp_id = rfp_options[selected]
    st.session_state["current_rfp_id"] = rfp_id
    
    st.markdown("---")
    
    # Fetch RFP details
    details = get_rfp_details(rfp_id)
    
    if not details:
        st.error(f"Could not load RFP details for ID: {rfp_id}")
        return
    
    # === Document Information Section ===
    st.subheader("📄 Document Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**General Details**")
        info_container = st.container(border=True)
        with info_container:
            st.markdown(f"**📁 Filename:** `{details.get('filename', 'Unknown')}`")
            st.markdown(f"**🆔 RFP ID:** `{rfp_id}`")
            st.markdown(f"**👤 Client:** {details.get('client_name') or 'Not specified'}")
            st.markdown(f"**🏢 Sector:** {details.get('sector') or 'Not specified'}")
    
    with col2:
        st.markdown("**Processing Details**")
        info_container = st.container(border=True)
        with info_container:
            st.markdown(f"**📅 Created:** {format_datetime(details.get('created_at'))}")
            st.markdown(f"**📝 Deadline:** {details.get('submission_deadline') or 'Not specified'}")
            st.markdown(f"**📏 Text Length:** {details.get('text_length', 0):,} characters")
            ocr_status = "✅ Yes" if details.get('ocr_used') else "❌ No"
            st.markdown(f"**🔍 OCR Used:** {ocr_status}")
    
    # Status badge
    status = details.get("status", "unknown")
    status_config = {
        "uploaded": ("🟡", "warning", "Document uploaded, awaiting analysis"),
        "analyzed": ("🟢", "success", "Analysis complete"),
        "failed": ("🔴", "error", "Analysis failed")
    }
    
    emoji, color, desc = status_config.get(status, ("⚪", "info", "Unknown status"))
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if color == "success":
            st.success(f"{emoji} **Status: {status.title()}** - {desc}")
        elif color == "warning":
            st.warning(f"{emoji} **Status: {status.title()}** - {desc}")
        elif color == "error":
            st.error(f"{emoji} **Status: {status.title()}** - {desc}")
        else:
            st.info(f"{emoji} **Status: {status.title()}** - {desc}")
    
    st.markdown("---")
    
    # === Analysis Status Section ===
    st.subheader("🔬 Analysis Status")
    
    analysis_status = get_analysis_status(rfp_id)
    analysis_results = get_analysis_results(rfp_id)
    
    # Show current job status if running
    if analysis_status and analysis_status.get("has_job"):
        job_status = analysis_status.get("status", "unknown")
        
        if job_status in ["queued", "running"]:
            st.info(f"🔄 **Analysis in progress** - {analysis_status.get('step_description', 'Working...')}")
            
            # Progress bar
            progress = analysis_status.get("progress_percent", 0) / 100
            st.progress(progress, text=f"Step {analysis_status.get('current_step', 0)}/5")
            
            # Recent logs
            logs = analysis_status.get("logs", [])
            if logs:
                with st.expander("📜 Recent Logs", expanded=False):
                    for log in logs[-5:]:
                        st.text(log)
            
            # Auto-refresh button
            if st.button("🔄 Refresh Status"):
                st.rerun()
        
        elif job_status == "completed":
            st.success("✅ **Analysis completed successfully!**")
            
            # Show results summary
            summary = analysis_status.get("results_summary", {})
            if summary:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Requirements", summary.get("requirements_count", 0))
                with col2:
                    compliance_score = summary.get("compliance_score")
                    st.metric("Compliance", f"{compliance_score}%" if compliance_score else "N/A")
                with col3:
                    quality_score = summary.get("quality_score")
                    st.metric("Quality", f"{quality_score}/10" if quality_score else "N/A")
                with col4:
                    st.metric("Recommendation", summary.get("recommendation", "N/A"))
        
        elif job_status == "failed":
            err_msg = analysis_status.get("error", "Unknown error")
            st.error(f"❌ **Analysis failed:** {err_msg}")
    
    # Show analysis results if available
    if analysis_results and analysis_results.get("outputs"):
        outputs = analysis_results["outputs"]
        available_outputs = [k for k, v in outputs.items() if v]
        
        if available_outputs:
            st.markdown("**Available Analysis Results:**")
            cols = st.columns(5)
            output_names = ["analysis", "compliance", "experience", "proposal", "review"]
            output_icons = {"analysis": "📝", "compliance": "✅", "experience": "🏆", "proposal": "📄", "review": "🔍"}
            
            for i, name in enumerate(output_names):
                with cols[i]:
                    if name in available_outputs:
                        st.success(f"{output_icons.get(name, '📋')} {name.title()}")
                    else:
                        st.warning(f"⏳ {name.title()}")
    
    # Analysis action buttons
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if status == "uploaded":
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                with st.spinner("Starting analysis..."):
                    result, error = trigger_analysis(rfp_id)
                if error:
                    st.error(f"Failed to start analysis: {error}")
                else:
                    st.success("Analysis started!")
                    st.session_state["current_job_id"] = result.get("job_id")
                    st.rerun()
        else:
            if st.button("🔄 Rerun Analysis", use_container_width=True):
                with st.spinner("Starting reanalysis..."):
                    result, error = rerun_analysis(rfp_id)
                if error:
                    st.error(f"Failed to start reanalysis: {error}")
                else:
                    st.success("Reanalysis started!")
                    st.session_state["current_job_id"] = result.get("job_id")
                    st.rerun()
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # === Text Preview Section ===
    st.subheader("📜 Extracted Text Preview")
    
    text_data = get_rfp_text(rfp_id)
    
    if text_data and text_data.get("text"):
        text = text_data["text"]
        text_length = len(text)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"*Total length: {text_length:,} characters*")
        with col2:
            preview_length = st.selectbox(
                "Preview length",
                options=[500, 1000, 2000, 5000],
                index=1,
                label_visibility="collapsed"
            )
        
        # Show text in a scrollable container
        preview_text = text[:preview_length]
        if len(text) > preview_length:
            preview_text += "\n\n... [truncated]"
        
        with st.container(border=True, height=300):
            st.text(preview_text)
        
        # Full text download
        st.download_button(
            label="📥 Download Full Text",
            data=text,
            file_name=f"{rfp_id}_extracted_text.txt",
            mime="text/plain"
        )
    else:
        st.warning("No extracted text available for this RFP.")
    
    st.markdown("---")
    
    # === Navigation Section ===
    st.subheader("🔗 Quick Navigation")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 Requirements", use_container_width=True, disabled=(status != "analyzed")):
            st.switch_page("pages/2_requirements.py")
    
    with col2:
        if st.button("✅ Compliance", use_container_width=True, disabled=(status != "analyzed")):
            st.switch_page("pages/3_compliance.py")
    
    with col3:
        if st.button("📄 Proposal", use_container_width=True, disabled=(status != "analyzed")):
            st.switch_page("pages/4_proposal.py")
    
    with col4:
        if st.button("📦 Export", use_container_width=True, disabled=(status != "analyzed")):
            st.switch_page("pages/5_export.py")
    
    if status != "analyzed":
        st.caption("*Analysis pages will be available after analysis is complete.*")
    
    st.markdown("---")
    
    # Back to upload
    if st.button("⬅️ Back to Upload"):
        st.switch_page("pages/1_upload.py")


if __name__ == "__main__":
    main()
