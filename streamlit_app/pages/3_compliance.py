"""
Compliance Page - Compliance Matrix Dashboard

Displays compliance matrix, risk flags, and allows status updates.
"""

import streamlit as st
import httpx
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Compliance", page_icon="✅", layout="wide")

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


def get_compliance(rfp_id):
    """Get compliance results for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/results/{rfp_id}/compliance", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("✅ Compliance Dashboard")
    st.markdown("Review compliance matrix, risk flags, and track requirement status.")
    
    # RFP selector
    rfps = get_rfps()
    
    if not rfps:
        st.warning("No RFPs found. Please upload an RFP first.")
        if st.button("📤 Go to Upload"):
            st.switch_page("pages/1_upload.py")
        return
    
    # Get current RFP from session or use first
    current_rfp = st.session_state.get("current_rfp_id")
    
    rfp_options = {f"{r['filename']} ({r['rfp_id']})": r['rfp_id'] for r in rfps}
    
    # Find index of current RFP
    default_index = 0
    if current_rfp:
        for i, (_, rfp_id) in enumerate(rfp_options.items()):
            if rfp_id == current_rfp:
                default_index = i
                break
    
    selected = st.selectbox(
        "Select RFP",
        options=list(rfp_options.keys()),
        index=default_index
    )
    
    rfp_id = rfp_options[selected]
    st.session_state["current_rfp_id"] = rfp_id
    
    # Get compliance data
    compliance = get_compliance(rfp_id)
    
    if not compliance:
        st.warning("Compliance analysis not yet complete.")
        
        # Import and use status component with rerun button
        from components.status_component import display_analysis_status
        
        st.markdown("---")
        status = display_analysis_status(
            rfp_id=rfp_id,
            auto_refresh=True,
            show_rerun_button=True
        )
        
        # If analysis completed, refresh to show results
        if status and status.get("status") == "completed":
            st.rerun()
        return
    
    # Summary metrics
    st.markdown("---")
    
    matrix = compliance.get("compliance_matrix", [])
    risk_flags = compliance.get("risk_flags", [])
    
    mandatory_items = [m for m in matrix if m.get("mandatory")]
    optional_items = [m for m in matrix if not m.get("mandatory")]
    
    high_risks = [r for r in risk_flags if r.get("risk_level") in ["high", "critical"]]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total Items", len(matrix))
    with col2:
        st.metric("🔴 Mandatory", len(mandatory_items))
    with col3:
        st.metric("🟢 Optional", len(optional_items))
    with col4:
        st.metric("⚠️ Risk Flags", len(risk_flags))
    with col5:
        st.metric("🚨 High Risk", len(high_risks))
    
    # Risk flags section
    if risk_flags:
        st.markdown("---")
        st.subheader("🚨 Risk Flags")
        
        for risk in sorted(risk_flags, key=lambda x: ["low", "medium", "high", "critical"].index(x.get("risk_level", "low")), reverse=True):
            level = risk.get("risk_level", "low")
            
            if level == "critical":
                alert_type = "error"
                icon = "🔴"
            elif level == "high":
                alert_type = "warning"
                icon = "🟠"
            elif level == "medium":
                alert_type = "info"
                icon = "🟡"
            else:
                alert_type = "success"
                icon = "🟢"
            
            with st.expander(f"{icon} **{risk.get('requirement_id')}** - {level.upper()}: {risk.get('category', 'General')}", expanded=(level in ["high", "critical"])):
                st.markdown(f"**Explanation:** {risk.get('explanation', 'No details')}")
                
                if risk.get("mitigation"):
                    st.markdown(f"**Suggested Mitigation:** {risk.get('mitigation')}")
    
    # Compliance matrix
    st.markdown("---")
    st.subheader("📊 Compliance Matrix")
    
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        filter_mandatory = st.radio("Show", ["All", "Mandatory Only", "Optional Only"], horizontal=True)
    with col2:
        filter_status = st.selectbox("Status Filter", ["All", "Pending", "Met", "Not Met", "Partial"])
    
    # Apply filters
    filtered_matrix = matrix
    
    if filter_mandatory == "Mandatory Only":
        filtered_matrix = [m for m in filtered_matrix if m.get("mandatory")]
    elif filter_mandatory == "Optional Only":
        filtered_matrix = [m for m in filtered_matrix if not m.get("mandatory")]
    
    if filter_status != "All":
        filtered_matrix = [m for m in filtered_matrix if m.get("status", "").lower() == filter_status.lower()]
    
    # Display matrix as table
    if filtered_matrix:
        st.markdown(f"**Showing {len(filtered_matrix)} items**")
        
        for item in filtered_matrix:
            col1, col2, col3, col4 = st.columns([1, 3, 1, 2])
            
            with col1:
                st.markdown(f"**{item.get('requirement_id', 'N/A')}**")
            
            with col2:
                text = item.get("requirement_text", "")
                st.write(text[:100] + "..." if len(text) > 100 else text)
            
            with col3:
                status = item.get("status", "pending")
                status_icons = {
                    "pending": "⏳",
                    "met": "✅",
                    "not_met": "❌",
                    "partial": "🔶",
                    "not_applicable": "➖"
                }
                st.write(f"{status_icons.get(status, '❓')} {status.title()}")
            
            with col4:
                if item.get("mandatory"):
                    st.markdown("🔴 **Mandatory**")
                else:
                    st.write("🟢 Optional")
            
            st.markdown("---")
    else:
        st.info("No items match your filters.")
    
    # Missing information
    if compliance.get("missing_information"):
        st.markdown("---")
        st.subheader("❓ Missing Information")
        st.warning("The following clarifications are needed:")
        
        for item in compliance["missing_information"]:
            st.markdown(f"- {item}")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 View Requirements", use_container_width=True):
            st.switch_page("pages/2_requirements.py")
    with col2:
        if st.button("📄 View Proposal", use_container_width=True, type="primary"):
            st.switch_page("pages/4_proposal.py")
    with col3:
        if st.button("📦 Export", use_container_width=True):
            st.switch_page("pages/5_export.py")


if __name__ == "__main__":
    main()
