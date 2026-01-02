"""
Upload Page - RFP Document Upload

Allows users to upload RFP documents (PDF/DOCX) with metadata.
"""

import streamlit as st
import httpx
from datetime import date
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Upload RFP", page_icon="📤", layout="wide")

API_BASE = "http://localhost:8000"


def upload_document(file, client_name, sector, deadline):
    """Upload document to API."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {
            "client_name": client_name or "",
            "sector": sector or "",
            "submission_deadline": str(deadline) if deadline else ""
        }
        
        response = httpx.post(
            f"{API_BASE}/api/documents/upload",
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.text
    except Exception as e:
        return None, str(e)


def trigger_analysis(rfp_id):
    """Trigger analysis workflow."""
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


def main():
    st.title("📤 Upload RFP Document")
    st.markdown("Upload your RFP document (PDF or DOCX) for AI-powered analysis.")
    
    st.markdown("---")
    
    # Upload form
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📁 Document Upload")
        
        uploaded_file = st.file_uploader(
            "Choose an RFP document",
            type=["pdf", "docx"],
            help="Upload a PDF or DOCX file. Scanned documents will be processed with OCR."
        )
        
        if uploaded_file:
            st.success(f"✅ File selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    
    with col2:
        st.subheader("📝 Metadata (Optional)")
        
        client_name = st.text_input(
            "Client Name",
            placeholder="e.g., Department of Defense",
            help="The organization issuing the RFP"
        )
        
        sector = st.selectbox(
            "Industry Sector",
            options=[
                "",
                "Government - Federal",
                "Government - State/Local",
                "Healthcare",
                "Finance",
                "Technology",
                "Manufacturing",
                "Construction",
                "Professional Services",
                "Other"
            ],
            help="Select the industry sector"
        )
        
        deadline = st.date_input(
            "Submission Deadline",
            value=None,
            min_value=date.today(),
            help="When is the proposal due?"
        )
    
    st.markdown("---")
    
    # Upload button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        upload_clicked = st.button(
            "🚀 Upload & Analyze",
            use_container_width=True,
            type="primary",
            disabled=uploaded_file is None
        )
    
    if upload_clicked and uploaded_file:
        with st.spinner("Uploading document..."):
            result, error = upload_document(
                uploaded_file,
                client_name,
                sector if sector else None,
                deadline
            )
        
        if error:
            st.error(f"❌ Upload failed: {error}")
        else:
            st.success(f"✅ Document uploaded successfully!")
            
            # Show upload result
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("RFP ID", result["rfp_id"])
            with col2:
                st.metric("Text Length", f"{result['text_length']:,} chars")
            with col3:
                st.metric("OCR Used", "Yes" if result["ocr_used"] else "No")
            
            if result.get("warnings"):
                for warning in result["warnings"]:
                    st.warning(f"⚠️ {warning}")
            
            # Store in session
            st.session_state["current_rfp_id"] = result["rfp_id"]
            
            # Trigger analysis
            st.markdown("---")
            st.subheader("🔄 Starting Analysis...")
            
            with st.spinner("Triggering AI analysis workflow..."):
                analysis_result, analysis_error = trigger_analysis(result["rfp_id"])
            
            if analysis_error:
                st.error(f"❌ Failed to start analysis: {analysis_error}")
            else:
                st.success("✅ Analysis workflow started!")
                
                # Store job ID in session for tracking
                st.session_state["current_job_id"] = analysis_result['job_id']
                
                # Import and use status component for real-time tracking
                from components.status_component import display_analysis_status
                
                st.markdown("---")
                st.subheader("📊 Analysis Progress")
                
                # Display status with auto-refresh
                display_analysis_status(
                    job_id=analysis_result['job_id'],
                    rfp_id=result["rfp_id"],
                    auto_refresh=True,
                    show_rerun_button=False
                )
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📝 View Requirements", use_container_width=True):
                        st.switch_page("pages/2_requirements.py")
                with col2:
                    if st.button("✅ View Compliance", use_container_width=True):
                        st.switch_page("pages/3_compliance.py")
    
    # Recent uploads section
    st.markdown("---")
    st.subheader("📋 Recent Uploads")
    
    try:
        response = httpx.get(f"{API_BASE}/api/documents/", timeout=10)
        if response.status_code == 200:
            rfps = response.json()
            
            if rfps:
                for rfp in rfps[:5]:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.write(f"📄 **{rfp.get('filename', 'Unknown')}**")
                        with col2:
                            st.write(rfp.get("client_name") or "No client")
                        with col3:
                            status = rfp.get("status", "unknown")
                            status_colors = {
                                "uploaded": "🟡",
                                "analyzed": "🟢",
                                "failed": "🔴"
                            }
                            st.write(f"{status_colors.get(status, '⚪')} {status.title()}")
                        with col4:
                            if st.button("View", key=rfp["rfp_id"]):
                                st.session_state["current_rfp_id"] = rfp["rfp_id"]
                                st.switch_page("pages/0_details.py")
            else:
                st.info("No RFPs uploaded yet.")
        else:
            st.warning("Could not load recent uploads.")
    except:
        st.warning("API not available. Start the API server to see recent uploads.")


if __name__ == "__main__":
    main()
