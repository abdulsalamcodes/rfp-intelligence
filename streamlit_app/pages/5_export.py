"""
Export Page - Document Export

Export compliance matrix and proposal documents in various formats.
"""

import streamlit as st
import httpx
import json
import csv
import io
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Export", page_icon="📦", layout="wide")

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


def get_results(rfp_id):
    """Get all results for an RFP."""
    try:
        response = httpx.get(f"{API_BASE}/api/results/{rfp_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def generate_compliance_csv(compliance):
    """Generate CSV for compliance matrix."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Requirement ID",
        "Requirement Text",
        "Mandatory",
        "Status",
        "Notes"
    ])
    
    # Data
    for item in compliance.get("compliance_matrix", []):
        writer.writerow([
            item.get("requirement_id", ""),
            item.get("requirement_text", ""),
            "Yes" if item.get("mandatory") else "No",
            item.get("status", "pending"),
            item.get("notes", "")
        ])
    
    return output.getvalue()


def generate_proposal_markdown(proposal, review, analysis):
    """Generate Markdown for proposal document."""
    lines = []
    
    # Title
    lines.append(f"# Technical Proposal")
    lines.append(f"")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")
    
    # Summary
    if analysis and analysis.get("summary"):
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(analysis["summary"])
        lines.append("")
    
    # Overall approach
    if proposal.get("overall_approach_summary"):
        lines.append("## Overall Approach")
        lines.append("")
        lines.append(proposal["overall_approach_summary"])
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Sections
    for section in proposal.get("sections", []):
        lines.append(f"## {section.get('title', 'Section')}")
        lines.append("")
        lines.append(section.get("content", ""))
        lines.append("")
        
        if section.get("assumptions"):
            lines.append("### Assumptions")
            lines.append("")
            for assumption in section["assumptions"]:
                lines.append(f"- {assumption}")
            lines.append("")
        
        if section.get("source_references"):
            lines.append(f"*References: {', '.join(section['source_references'])}*")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Quality review summary
    if review:
        lines.append("## Quality Review Summary")
        lines.append("")
        lines.append(f"**Quality Score:** {review.get('overall_quality_score', 0):.0%}")
        lines.append(f"")
        lines.append(f"**Recommendation:** {review.get('recommendation', 'Unknown').replace('_', ' ').title()}")
        lines.append("")
        
        if review.get("priority_fixes"):
            lines.append("### Priority Fixes")
            lines.append("")
            for fix in review["priority_fixes"]:
                lines.append(f"- {fix}")
            lines.append("")
    
    return "\n".join(lines)


def generate_summary_json(results):
    """Generate JSON summary of all results."""
    return json.dumps(results, indent=2, default=str)


def main():
    st.title("📦 Export Documents")
    st.markdown("Download compliance matrix, proposal, and summary documents.")
    
    # RFP selector
    rfps = get_rfps()
    
    if not rfps:
        st.warning("No RFPs found. Please upload an RFP first.")
        if st.button("📤 Go to Upload"):
            st.switch_page("pages/1_upload.py")
        return
    
    current_rfp = st.session_state.get("current_rfp_id")
    rfp_options = {f"{r['filename']} ({r['rfp_id']})": r['rfp_id'] for r in rfps}
    
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
    
    # Get results
    results = get_results(rfp_id)
    
    if not results:
        st.warning("No results available for this RFP.")
        return
    
    outputs = results.get("outputs", {})
    metadata = results.get("metadata", {})
    
    # Summary
    st.markdown("---")
    st.subheader("📊 Export Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        has_analysis = "analysis" in outputs
        st.metric("Analysis", "✅ Ready" if has_analysis else "❌ Missing")
    with col2:
        has_compliance = "compliance" in outputs
        st.metric("Compliance", "✅ Ready" if has_compliance else "❌ Missing")
    with col3:
        has_proposal = "proposal" in outputs
        st.metric("Proposal", "✅ Ready" if has_proposal else "❌ Missing")
    with col4:
        has_review = "review" in outputs
        st.metric("Review", "✅ Ready" if has_review else "❌ Missing")
    
    # Export options
    st.markdown("---")
    st.subheader("📥 Download Files")
    
    col1, col2, col3 = st.columns(3)
    
    # Compliance Matrix CSV
    with col1:
        st.markdown("### 📋 Compliance Matrix")
        
        if has_compliance:
            csv_content = generate_compliance_csv(outputs["compliance"])
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_content,
                file_name=f"{rfp_id}_compliance_matrix.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption(f"{len(outputs['compliance'].get('compliance_matrix', []))} items")
        else:
            st.warning("Not available")
    
    # Proposal Markdown
    with col2:
        st.markdown("### 📄 Proposal Document")
        
        if has_proposal:
            md_content = generate_proposal_markdown(
                outputs["proposal"],
                outputs.get("review"),
                outputs.get("analysis")
            )
            st.download_button(
                label="⬇️ Download Markdown",
                data=md_content,
                file_name=f"{rfp_id}_proposal.md",
                mime="text/markdown",
                use_container_width=True
            )
            section_count = len(outputs["proposal"].get("sections", []))
            st.caption(f"{section_count} sections")
        else:
            st.warning("Not available")
    
    # Full JSON Export
    with col3:
        st.markdown("### 📊 Full Data Export")
        
        json_content = generate_summary_json(results)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_content,
            file_name=f"{rfp_id}_full_export.json",
            mime="application/json",
            use_container_width=True
        )
        st.caption("All data")
    
    # Export preview
    st.markdown("---")
    st.subheader("👁️ Preview")
    
    preview_tabs = st.tabs(["Compliance CSV", "Proposal Preview", "Raw JSON"])
    
    with preview_tabs[0]:
        if has_compliance:
            matrix = outputs["compliance"].get("compliance_matrix", [])
            if matrix:
                st.dataframe(
                    [
                        {
                            "ID": m.get("requirement_id"),
                            "Text": m.get("requirement_text", "")[:50] + "...",
                            "Mandatory": "Yes" if m.get("mandatory") else "No",
                            "Status": m.get("status")
                        }
                        for m in matrix[:20]
                    ],
                    use_container_width=True
                )
                if len(matrix) > 20:
                    st.caption(f"Showing 20 of {len(matrix)} items")
            else:
                st.info("No compliance data")
        else:
            st.info("Compliance data not available")
    
    with preview_tabs[1]:
        if has_proposal:
            for section in outputs["proposal"].get("sections", [])[:3]:
                with st.expander(section.get("title", "Section")):
                    st.markdown(section.get("content", "")[:500] + "...")
            
            if len(outputs["proposal"].get("sections", [])) > 3:
                st.caption(f"Showing 3 of {len(outputs['proposal'].get('sections', []))} sections")
        else:
            st.info("Proposal data not available")
    
    with preview_tabs[2]:
        st.json(results.get("metadata", {}))
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Back to Proposal", use_container_width=True):
            st.switch_page("pages/4_proposal.py")
    with col2:
        if st.button("📤 Upload New RFP", use_container_width=True):
            st.switch_page("pages/1_upload.py")
    with col3:
        if st.button("🏠 Dashboard", use_container_width=True, type="primary"):
            st.switch_page("app.py")


if __name__ == "__main__":
    main()
