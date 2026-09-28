"""
Agentic RFP Evaluation and Supplier Ranking

This is the main Streamlit application file.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd

# Import our database helper functions
from src.database import get_active_criteria, get_total_weight

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

    # =========================================================================
    # SECTION 1: EVALUATION CRITERIA
    # =========================================================================
    st.markdown("---")
    st.header("📊 Evaluation Criteria")
    st.write("These are the active criteria used to evaluate supplier proposals:")

    # Fetch criteria from database
    try:
        criteria = get_active_criteria()
        total_weight = get_total_weight()

        if criteria:
            # Convert to pandas DataFrame for nice display
            df = pd.DataFrame(criteria)

            # Rename columns for better display
            df = df.rename(columns={
                'criterion_id': 'ID',
                'name': 'Criterion',
                'description': 'What to Evaluate',
                'weight': 'Weight (%)',
                'max_score': 'Max Score'
            })

            # Display the table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # Show total weight with validation
            if total_weight == 100.0:
                st.success(f"✅ Total Weight: {total_weight}% (Valid)")
            else:
                st.error(f"❌ Total Weight: {total_weight}% (Must be 100%)")

        else:
            st.warning("No active criteria found. Please run database/init_db.py first.")

    except FileNotFoundError as e:
        st.error(f"❌ Database Error: {e}")
        st.info("💡 Run this command to set up the database: `python database/init_db.py`")

    # =========================================================================
    # SECTION 2: SYSTEM STATUS
    # =========================================================================
    st.markdown("---")
    st.header("🔧 System Status")

    # Create three columns for status info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Database",
            value="Connected" if criteria else "Error",
            delta="Ready" if criteria else "Check Setup"
        )

    with col2:
        st.metric(
            label="Criteria Loaded",
            value=f"{len(criteria)} Active" if criteria else "0",
            delta=f"{total_weight}% Weight" if criteria else "N/A"
        )

    with col3:
        st.metric(
            label="System",
            value="Ready" if criteria and total_weight == 100 else "Check Config",
            delta="Operational" if criteria and total_weight == 100 else "Needs Attention"
        )

    # Footer
    st.markdown("---")
    st.caption("Built for IIT Roorkee - Agentic AI Mini Project")


# =============================================================================
# RUN THE APP
# =============================================================================
if __name__ == "__main__":
    main()
