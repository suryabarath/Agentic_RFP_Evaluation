"""
Agentic RFP Evaluation and Supplier Ranking

This is the main Streamlit application file.
Run with: streamlit run app.py
"""

import streamlit as st

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
# This MUST be the first Streamlit command
st.set_page_config(
    page_title="RFP Evaluation System",
    page_icon="📋",
    layout="wide"
)

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main function that runs the Streamlit app."""

    # Title and description
    st.title("📋 Agentic RFP Evaluation System")
    st.markdown("---")

    # Welcome message
    st.write("""
    Welcome to the **RFP Evaluation and Supplier Ranking System**!

    This application helps you:
    - Upload supplier proposal PDFs
    - Evaluate proposals using AI
    - Score and rank suppliers automatically
    - Export results for further analysis
    """)

    # Status indicator
    st.success("✅ Application is running successfully!")

    # Show some basic info
    st.markdown("---")
    st.subheader("System Status")

    # Create three columns for status info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Database", value="Connected", delta="Ready")

    with col2:
        st.metric(label="Criteria", value="5 Active", delta="100% Weight")

    with col3:
        st.metric(label="Status", value="Ready", delta="Operational")

    # Footer
    st.markdown("---")
    st.caption("Built for IIT Roorkee - Agentic AI Mini Project")


# =============================================================================
# RUN THE APP
# =============================================================================
if __name__ == "__main__":
    main()
