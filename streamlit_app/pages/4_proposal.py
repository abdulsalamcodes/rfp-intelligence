"""
Proposal Page - Edit Proposal Sections

Allows editing of AI-generated proposal sections with review comments sidebar.
"""

import streamlit as st
import httpx
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Proposal Editor", page_icon="📄", layout="wide")

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



def regenerate_proposal(rfp_id: str):
    """Trigger the proposal drafting agent to regenerate the proposal."""
    try:
        response = httpx.post(
            f"{API_BASE}/api/agents/proposal",
            json={"rfp_id": rfp_id, "agent_name": "proposal"},
            timeout=120  # Longer timeout for LLM processing
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.text
    except Exception as e:
        return None, str(e)


def revise_proposal_with_ai(rfp_id: str):
    """Revise the proposal using AI based on review feedback."""
    try:
        response = httpx.post(
            f"{API_BASE}/api/proposal/{rfp_id}/revise",
            timeout=180  # Longer timeout as this involves reading + writing
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.text
    except Exception as e:
        return None, str(e)


def main():
    st.title("📄 Proposal Editor")
    st.markdown("Review and edit AI-generated proposal sections.")
    
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
    
    # Get all results
    results = get_results(rfp_id)
    
    if not results or not results.get("outputs", {}).get("proposal"):
        st.warning("Proposal not yet generated. Please run the full analysis workflow.")
        if st.button("🔄 Refresh"):
            st.rerun()
        return
    
    proposal = results["outputs"]["proposal"]
    review = results["outputs"].get("review", {})
    experience = results["outputs"].get("experience", {})
    
    # Layout: Main content + Review sidebar
    main_col, sidebar_col = st.columns([3, 1])
    
    with sidebar_col:
        st.markdown("### 📋 Review Summary")
        
        quality_score = review.get("overall_quality_score", 0)
        recommendation = review.get("recommendation", "Unknown")
        
        # Quality gauge
        if quality_score >= 0.8:
            st.success(f"✅ Quality: {quality_score:.0%}")
        elif quality_score >= 0.6:
            st.warning(f"⚠️ Quality: {quality_score:.0%}")
        else:
            st.error(f"❌ Quality: {quality_score:.0%}")
        
        # Recommendation
        rec_colors = {
            "ready_with_minor_edits": "success",
            "needs_revision": "warning",
            "needs_major_revision": "error"
        }
        rec_func = getattr(st, rec_colors.get(recommendation, "info"))
        rec_func(f"**{recommendation.replace('_', ' ').title()}**")
        
        # Critical issues
        critical_count = review.get("critical_issues_count", 0)
        if critical_count > 0:
            st.error(f"🚨 {critical_count} Critical Issues")
        
        st.markdown("---")
        
        # Priority fixes
        if review.get("priority_fixes"):
            st.markdown("### 🔧 Priority Fixes")
            for i, fix in enumerate(review["priority_fixes"][:5], 1):
                st.markdown(f"{i}. {fix}")
        
        st.markdown("---")
        
        # Experience gaps
        if experience.get("gaps"):
            st.markdown("### ⚠️ Experience Gaps")
            for gap in experience["gaps"][:3]:
                st.warning(f"**{gap.get('requirement_id')}**: {gap.get('gap_description', '')[:50]}...")
    
    with main_col:
        sections = proposal.get("sections", [])
        
        if not sections:
            st.info("No proposal sections generated yet.")
            return
        
        # Overall approach
        if proposal.get("overall_approach_summary"):
            st.markdown("### 📋 Overall Approach")
            st.info(proposal["overall_approach_summary"])
        
        st.markdown("---")
        
        # Section tabs
        section_titles = [s.get("title", f"Section {i+1}") for i, s in enumerate(sections)]
        tabs = st.tabs(section_titles)
        
        for tab, section in zip(tabs, sections):
            with tab:
                title = section.get("title", "Untitled Section")
                content = section.get("content", "")
                assumptions = section.get("assumptions", [])
                references = section.get("source_references", [])
                
                # Section header with metadata
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"## {title}")
                with col2:
                    word_count = len(content.split())
                    st.metric("Words", word_count)
                
                # References
                if references:
                    st.markdown("**📎 References:** " + ", ".join(references))
                
                st.markdown("---")
                
                # Get review items for this section
                section_reviews = [r for r in review.get("review_items", []) 
                                 if r.get("section") == title]
                
                if section_reviews:
                    with st.expander(f"⚠️ {len(section_reviews)} Review Comments", expanded=True):
                        for item in section_reviews:
                            severity = item.get("severity", "low")
                            if severity == "critical":
                                st.error(f"🔴 **{item.get('issue_type', 'Issue').upper()}**: {item.get('description', '')}")
                            elif severity == "high":
                                st.warning(f"🟠 **{item.get('issue_type', 'Issue')}**: {item.get('description', '')}")
                            else:
                                st.info(f"🔵 **{item.get('issue_type', 'Issue')}**: {item.get('description', '')}")
                            
                            if item.get("suggested_fix"):
                                st.markdown(f"💡 *Fix: {item.get('suggested_fix')}*")
                
                # Editable content
                st.markdown("### ✏️ Content")
                
                # Initialize session state for edited content
                edit_key = f"edit_{rfp_id}_{title}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = content
                
                edited_content = st.text_area(
                    "Edit section content",
                    value=st.session_state[edit_key],
                    height=400,
                    key=f"textarea_{title}",
                    label_visibility="collapsed"
                )
                
                # Track changes
                if edited_content != st.session_state[edit_key]:
                    st.session_state[edit_key] = edited_content
                    st.success("✅ Changes saved locally")
                
                # Assumptions
                if assumptions:
                    st.markdown("---")
                    st.markdown("### ⚠️ Assumptions")
                    for assumption in assumptions:
                        st.markdown(f"- {assumption}")
    
    # Navigation and actions
    st.markdown("---")
    
    # First row: AI-powered actions
    st.markdown("### 🤖 AI Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        # Check if review exists for enabling the revise button
        has_review = bool(review.get("review_items"))
        if st.button(
            "✨ Revise with AI", 
            use_container_width=True, 
            type="primary",
            disabled=not has_review,
            help="Let AI revise the proposal based on review feedback" if has_review else "Review feedback required for AI revision"
        ):
            with st.spinner("AI is revising the proposal based on review feedback... This may take 1-2 minutes."):
                result, error = revise_proposal_with_ai(rfp_id)
            if error:
                st.error(f"❌ Failed to revise: {error}")
            else:
                st.success("✅ Proposal revised successfully!")
                if result.get("revision_summary"):
                    st.info(f"**Revision Summary:** {result['revision_summary']}")
                st.rerun()
    
    with col2:
        if st.button("🔄 Re-generate from Scratch", use_container_width=True):
            with st.spinner("Regenerating proposal... This may take a minute."):
                result, error = regenerate_proposal(rfp_id)
            if error:
                st.error(f"❌ Failed to regenerate: {error}")
            else:
                st.success("✅ Proposal regenerated successfully!")
                st.rerun()
    
    st.caption("💡 **Revise with AI** improves the existing proposal using review feedback. **Re-generate** creates a completely new proposal.")
    
    # Second row: Navigation and manual actions
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Compliance", use_container_width=True):
            st.switch_page("pages/3_compliance.py")
    with col2:
        if st.button("🔍 Re-run Review", use_container_width=True):
            # Trigger review agent to re-review the current proposal
            try:
                with st.spinner("Re-running review..."):
                    response = httpx.post(
                        f"{API_BASE}/api/agents/review",
                        json={"rfp_id": rfp_id, "agent_name": "review"},
                        timeout=120
                    )
                if response.status_code == 200:
                    st.success("✅ Review updated!")
                    st.rerun()
                else:
                    st.error(f"Failed to re-run review: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    with col3:
        if st.button("💾 Save All Edits", use_container_width=True):
            st.success("✅ All edits saved!")
    with col4:
        if st.button("📦 Export", use_container_width=True):
            st.switch_page("pages/5_export.py")


if __name__ == "__main__":
    main()
