"""
Requirements Page - View Extracted Requirements

Displays requirements extracted from the RFP with confidence scores and filtering.
"""

import streamlit as st
import httpx
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Requirements", page_icon="📝", layout="wide")

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


def get_analysis(rfp_id):
    """Get analysis results for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/results/{rfp_id}/analysis", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def main():
    st.title("📝 Extracted Requirements")
    st.markdown("View and filter requirements extracted from your RFP documents.")
    
    # RFP selector
    rfps = get_rfps()
    
    if not rfps:
        st.warning("No RFPs found. Please upload an RFP first.")
        if st.button("📤 Go to Upload"):
            st.switch_page("pages/1_upload.py")
        return
    
    # Select RFP
    rfp_options = {f"{r['filename']} ({r['rfp_id']})": r['rfp_id'] for r in rfps}
    
    selected = st.selectbox(
        "Select RFP",
        options=list(rfp_options.keys()),
        index=0
    )
    
    rfp_id = rfp_options[selected]
    
    # Get analysis
    analysis = get_analysis(rfp_id)
    
    if not analysis:
        st.warning("Analysis not yet complete. Please wait or trigger analysis.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh"):
                st.rerun()
        with col2:
            if st.button("📤 Re-upload"):
                st.switch_page("pages/1_upload.py")
        return
    
    # Summary section
    st.markdown("---")
    st.subheader("📋 RFP Summary")
    st.info(analysis.get("summary", "No summary available"))
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    requirements = analysis.get("requirements", [])
    mandatory = [r for r in requirements if r.get("mandatory")]
    optional = [r for r in requirements if not r.get("mandatory")]
    
    with col1:
        st.metric("Total Requirements", len(requirements))
    with col2:
        st.metric("Mandatory", len(mandatory))
    with col3:
        st.metric("Optional", len(optional))
    with col4:
        avg_confidence = sum(r.get("confidence", 0) for r in requirements) / len(requirements) if requirements else 0
        st.metric("Avg Confidence", f"{avg_confidence:.0%}")
    
    # Filters
    st.markdown("---")
    st.subheader("🔍 Filter Requirements")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_type = st.radio(
            "Type",
            options=["All", "Mandatory", "Optional"],
            horizontal=True
        )
    
    with col2:
        categories = list(set(r.get("category", "Other") for r in requirements if r.get("category")))
        filter_category = st.selectbox(
            "Category",
            options=["All"] + sorted(categories)
        )
    
    with col3:
        filter_confidence = st.slider(
            "Min Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1
        )
    
    # Search
    search_query = st.text_input("🔎 Search requirements", placeholder="Enter keywords...")
    
    # Apply filters
    filtered = requirements
    
    if filter_type == "Mandatory":
        filtered = [r for r in filtered if r.get("mandatory")]
    elif filter_type == "Optional":
        filtered = [r for r in filtered if not r.get("mandatory")]
    
    if filter_category != "All":
        filtered = [r for r in filtered if r.get("category") == filter_category]
    
    filtered = [r for r in filtered if r.get("confidence", 0) >= filter_confidence]
    
    if search_query:
        filtered = [r for r in filtered if search_query.lower() in r.get("text", "").lower()]
    
    # Display requirements
    st.markdown("---")
    st.subheader(f"📄 Requirements ({len(filtered)} shown)")
    
    if not filtered:
        st.info("No requirements match your filters.")
    else:
        for req in filtered:
            with st.expander(f"**{req.get('id', 'REQ-?')}** - {req.get('text', '')[:80]}...", expanded=False):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown("**Full Text:**")
                    st.write(req.get("text", ""))
                
                with col2:
                    st.markdown("**Type:**")
                    if req.get("mandatory"):
                        st.error("🔴 Mandatory")
                    else:
                        st.success("🟢 Optional")
                    
                    st.markdown("**Category:**")
                    st.write(req.get("category", "Other"))
                
                with col3:
                    st.markdown("**Confidence:**")
                    confidence = req.get("confidence", 0)
                    if confidence >= 0.9:
                        st.success(f"✅ {confidence:.0%}")
                    elif confidence >= 0.7:
                        st.warning(f"⚠️ {confidence:.0%}")
                    else:
                        st.error(f"❓ {confidence:.0%}")
                    
                    st.markdown("**Source:**")
                    st.write(req.get("source_section", "Not specified"))
    
    # Deadlines section
    if analysis.get("deadlines"):
        st.markdown("---")
        st.subheader("📅 Key Deadlines")
        
        deadlines = analysis["deadlines"]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📤 Submission", deadlines.get("submission") or "Not specified")
        with col2:
            st.metric("❓ Questions Due", deadlines.get("questions") or "Not specified")
        with col3:
            st.metric("🏢 Site Visit", deadlines.get("site_visit") or "N/A")
        with col4:
            st.metric("📝 Contract Start", deadlines.get("contract_start") or "Not specified")
    
    # Mandatory documents
    if analysis.get("mandatory_documents"):
        st.markdown("---")
        st.subheader("📎 Required Documents")
        
        for doc in analysis["mandatory_documents"]:
            st.markdown(f"- 📄 {doc}")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Back to Upload", use_container_width=True):
            st.switch_page("pages/1_upload.py")
    with col2:
        if st.button("✅ View Compliance", use_container_width=True, type="primary"):
            st.session_state["current_rfp_id"] = rfp_id
            st.switch_page("pages/3_compliance.py")
    with col3:
        if st.button("📄 View Proposal", use_container_width=True):
            st.session_state["current_rfp_id"] = rfp_id
            st.switch_page("pages/4_proposal.py")


if __name__ == "__main__":
    main()
