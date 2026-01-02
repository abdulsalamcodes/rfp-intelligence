"""
RFP Intelligence - Streamlit Application

Main application entry point with page configuration and navigation.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Main application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="RFP Intelligence",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #6b7280;
            margin-bottom: 2rem;
        }
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        .status-pending { background-color: #fef3c7; color: #92400e; }
        .status-analyzing { background-color: #dbeafe; color: #1e40af; }
        .status-completed { background-color: #d1fae5; color: #065f46; }
        .status-failed { background-color: #fee2e2; color: #991b1b; }
        .metric-card {
            background-color: #f9fafb;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid #e5e7eb;
        }
        .risk-high { color: #dc2626; font-weight: 600; }
        .risk-medium { color: #d97706; font-weight: 600; }
        .risk-low { color: #059669; }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=RFP+Intel", width=150)
        st.markdown("---")
        
        st.markdown("### 📋 Navigation")
        
        # Navigation info
        st.info("""
        **Pages:**
        - 📤 Upload - Submit RFPs
        - 📝 Requirements - View extracted requirements
        - ✅ Compliance - Review compliance matrix
        - 📄 Proposal - Edit draft sections
        - 📦 Export - Download documents
        """)
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        # API connection status
        api_status = st.empty()
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                api_status.success("✅ API Connected")
            else:
                api_status.warning("⚠️ API Error")
        except:
            api_status.error("❌ API Offline")
        
        st.markdown("---")
        st.caption("RFP Intelligence v1.0.0")
    
    # Main content
    st.markdown('<p class="main-header">📋 RFP Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered RFP analysis and proposal generation</p>', unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Total RFPs", "0", help="Total RFPs uploaded")
    with col2:
        st.metric("⏳ In Progress", "0", help="RFPs currently being analyzed")
    with col3:
        st.metric("✅ Completed", "0", help="RFPs with completed analysis")
    with col4:
        st.metric("📤 Exported", "0", help="Proposals exported")
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Upload New RFP", use_container_width=True, type="primary"):
            st.switch_page("pages/1_upload.py")
    
    with col2:
        if st.button("📋 View Recent RFPs", use_container_width=True):
            st.switch_page("pages/2_requirements.py")
    
    with col3:
        if st.button("📄 Continue Proposal", use_container_width=True):
            st.switch_page("pages/4_proposal.py")
    
    # Recent activity
    st.markdown("---")
    st.markdown("### 📊 Recent Activity")
    
    st.info("No recent activity. Upload an RFP to get started!")
    
    # Getting started guide
    with st.expander("📖 Getting Started Guide", expanded=True):
        st.markdown("""
        ### How to use RFP Intelligence
        
        1. **Upload an RFP** - Go to the Upload page and submit your RFP document (PDF or DOCX)
        2. **Review Requirements** - The AI will extract and categorize all requirements
        3. **Check Compliance** - Review the compliance matrix and risk flags
        4. **Edit Proposal** - Review and edit AI-generated proposal sections
        5. **Export** - Download the final compliance matrix and proposal documents
        
        ### Tips for Best Results
        
        - Use high-quality PDF documents (not scanned if possible)
        - Provide metadata (client name, sector, deadline) for better analysis
        - Review and edit AI-generated content before export
        - Add your own past projects and personnel data for better experience matching
        """)


if __name__ == "__main__":
    main()
