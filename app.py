"""
Agentic RFP Evaluation and Supplier Ranking

This is the main Streamlit application file.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date

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
            criteria = []  # Set empty list so later code doesn't break
            total_weight = 0

    except FileNotFoundError as e:
        st.error(f"❌ Database Error: {e}")
        st.info("💡 Run this command to set up the database: `python database/init_db.py`")
        criteria = []
        total_weight = 0

    # =========================================================================
    # SECTION 2: SUPPLIER INPUT
    # =========================================================================
    st.markdown("---")
    st.header("📤 Supplier Proposal Upload")
    st.write("Upload supplier proposals for evaluation. You can add multiple suppliers.")

    # Initialize session state for storing suppliers
    # Session state persists data across Streamlit reruns
    if 'suppliers' not in st.session_state:
        st.session_state.suppliers = []

    # Number of suppliers to evaluate
    num_suppliers = st.number_input(
        "How many suppliers do you want to evaluate?",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        help="Enter the number of supplier proposals you want to compare"
    )

    st.markdown("---")

    # Create input fields for each supplier
    suppliers_data = []
    all_valid = True  # Track if all inputs are valid

    for i in range(int(num_suppliers)):
        st.subheader(f"Supplier {i + 1}")

        # Create three columns for inputs
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            # Supplier name input
            supplier_name = st.text_input(
                "Supplier Name",
                key=f"name_{i}",
                placeholder="e.g., Apex Systems",
                help="Enter the supplier company name"
            )

            # PDF file uploader
            pdf_file = st.file_uploader(
                "Upload Proposal PDF",
                type=['pdf'],
                key=f"pdf_{i}",
                help="Upload the supplier's proposal document (PDF format only)"
            )

        with col2:
            # Submission date picker
            submission_date = st.date_input(
                "Submission Date",
                value=date.today(),
                key=f"date_{i}",
                help="When was this proposal submitted?"
            )

        with col3:
            # Experience rating slider
            experience_rating = st.slider(
                "Experience Rating",
                min_value=1,
                max_value=10,
                value=5,
                key=f"exp_{i}",
                help="Historical experience rating (1=Low, 10=High)"
            )

        # Validation for this supplier
        validation_errors = []

        if not supplier_name:
            validation_errors.append("Supplier name is required")

        if not pdf_file:
            validation_errors.append("PDF file is required")

        # Show validation status
        if validation_errors:
            all_valid = False
            for error in validation_errors:
                st.warning(f"⚠️ {error}")
        else:
            st.success(f"✅ {supplier_name} - Ready for evaluation")

            # Store valid supplier data
            suppliers_data.append({
                'name': supplier_name,
                'pdf_file': pdf_file,
                'submission_date': submission_date.strftime('%Y-%m-%d'),
                'experience_rating': experience_rating
            })

        st.markdown("---")

    # Summary and Evaluate button
    st.subheader("📋 Evaluation Summary")

    # Show summary of suppliers
    if suppliers_data:
        summary_df = pd.DataFrame([
            {
                'Supplier': s['name'],
                'Submission Date': s['submission_date'],
                'Experience Rating': f"{s['experience_rating']}/10",
                'PDF': s['pdf_file'].name if s['pdf_file'] else 'Not uploaded'
            }
            for s in suppliers_data
        ])
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.info(f"📊 Ready to evaluate **{len(suppliers_data)}** supplier(s) against **{len(criteria)}** criteria")
    else:
        st.warning("Please fill in all required fields for at least one supplier.")

    # Evaluate button
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

    with col_btn2:
        evaluate_button = st.button(
            "🚀 Evaluate Suppliers",
            type="primary",
            disabled=not all_valid or len(suppliers_data) == 0,
            use_container_width=True
        )

    if evaluate_button:
        st.session_state.suppliers = suppliers_data
        st.info("🔄 Evaluation will be implemented in the next phases...")
        # Store in session state for later use
        st.session_state.ready_for_evaluation = True

    # =========================================================================
    # SECTION 3: SYSTEM STATUS
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
