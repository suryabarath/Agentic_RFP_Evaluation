"""
Agentic RFP Evaluation and Supplier Ranking

This is the main Streamlit application file.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

# Import our modules
from src.database import (
    get_active_criteria, get_total_weight, save_pipeline_result,
    get_all_runs, get_run_summary
)
from src.pdf_tool import extract_text_from_uploaded_file, get_pdf_info, validate_pdf
from src.evaluator import evaluator
from src.orchestrator import Orchestrator, SupplierInput, PipelineResult
from src.config import config

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="RFP Evaluation System",
    page_icon="📋",
    layout="wide"
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_grade_color(grade: str) -> str:
    """Get color for PPI grade."""
    colors = {'A': 'green', 'B': 'blue', 'C': 'orange', 'D': 'red', 'F': 'darkred'}
    return colors.get(grade, 'gray')


def display_leaderboard(result: PipelineResult):
    """Display the evaluation leaderboard."""
    if not result.ranking or not result.ranking.rankings:
        st.warning("No ranking data available.")
        return

    st.subheader("🏆 Final Ranking")

    # Create leaderboard dataframe
    leaderboard_data = []
    for r in result.ranking.rankings:
        leaderboard_data.append({
            'Rank': f"#{r.rank}" + (" 🏆" if r.rank == 1 else ""),
            'Supplier': r.supplier_name,
            'Score': f"{r.weighted_score:.2f}",
            'PPI': f"{r.ppi_score:.2f}",
            'Grade': r.ppi_breakdown.ppi_grade if r.ppi_breakdown else 'N/A',
            'Risks': r.risk_count,
            'Warnings': r.warning_count
        })

    df = pd.DataFrame(leaderboard_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Show benchmarks
    if result.benchmarks:
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Best Score", f"{result.benchmarks.best_total_score:.2f}")
        with col2:
            st.metric("Average Score", f"{result.benchmarks.average_total_score:.2f}")
        with col3:
            st.metric("Worst Score", f"{result.benchmarks.worst_total_score:.2f}")
        with col4:
            st.metric("Spread (Std Dev)", f"{result.benchmarks.std_dev_total:.2f}")


def display_supplier_scorecard(supplier_result, benchmarks=None):
    """Display detailed scorecard for a supplier."""
    if not supplier_result.success:
        st.error(f"Evaluation failed: {supplier_result.error}")
        return

    score = supplier_result.score
    ppi = supplier_result.ppi
    gaps = supplier_result.gaps
    relative = supplier_result.relative

    # Header metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Weighted Score", f"{score.total_weighted_score:.2f}/100")
    with col2:
        if ppi:
            st.metric("PPI Score", f"{ppi.ppi_score:.2f}", delta=f"Grade: {ppi.ppi_grade}")
    with col3:
        if relative:
            st.metric("Rank", f"#{relative.rank}", delta=f"{relative.percentile:.0f}th %ile")
    with col4:
        warning_count = len(supplier_result.validation_warnings) if supplier_result.validation_warnings else 0
        st.metric("Warnings", warning_count, delta="⚠️" if warning_count > 0 else "✓")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Scores", "📈 Visual", "🔍 Gaps", "📋 Details", "⚠️ Warnings"])

    with tab1:
        # Criteria breakdown table
        st.markdown("**Criteria Breakdown:**")
        criteria_data = []
        for cs in score.criteria_scores:
            # Determine status emoji based on percentage
            if cs.percentage >= 80:
                status = "🟢"
            elif cs.percentage >= 60:
                status = "🟡"
            else:
                status = "🔴"

            criteria_data.append({
                'Status': status,
                'Criterion': cs.name,
                'Score': f"{cs.raw_score}/{cs.max_score}",
                'Percentage': f"{cs.percentage:.0f}%",
                'Weight': f"{cs.weight}%",
                'Contribution': f"{cs.weighted_score:.2f}"
            })

        df = pd.DataFrame(criteria_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Score calculation breakdown
        st.markdown("**Score Calculation:**")
        calc_text = " + ".join([f"{cs.weighted_score:.2f}" for cs in score.criteria_scores])
        st.code(f"{calc_text} = {score.total_weighted_score:.2f}")

    with tab2:
        # Visual progress bars for each criterion
        st.markdown("**Visual Score Breakdown:**")
        for cs in score.criteria_scores:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**{cs.name}**")
                st.caption(f"Weight: {cs.weight}%")
            with col2:
                # Progress bar
                st.progress(cs.percentage / 100)
                st.caption(f"{cs.raw_score}/{cs.max_score} ({cs.percentage:.0f}%) → {cs.weighted_score:.2f} points")

        # PPI breakdown if available
        if ppi:
            st.markdown("---")
            st.markdown("**PPI Breakdown:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Consistency", f"{ppi.consistency_score:.1f}%")
            with col2:
                st.metric("Quality", f"{ppi.quality_score:.1f}%")
            with col3:
                st.metric("Risk Penalty", f"-{ppi.risk_penalty:.1f}")

    with tab3:
        # Gap analysis
        if gaps:
            st.markdown(f"**Gap Analysis** (Potential improvement: +{gaps.max_potential_improvement:.2f} points)")

            if gaps.critical_gaps:
                st.error(f"🔴 **Critical Gaps** ({len(gaps.critical_gaps)})")
                for g in gaps.critical_gaps:
                    st.write(f"  • {g.name}: {g.percentage:.0f}% (need +{g.gap_to_threshold:.0f}% to reach 70%)")

            if gaps.high_gaps:
                st.warning(f"🟠 **High Gaps** ({len(gaps.high_gaps)})")
                for g in gaps.high_gaps:
                    st.write(f"  • {g.name}: {g.percentage:.0f}% (need +{g.gap_to_threshold:.0f}% to reach 70%)")

            if gaps.medium_gaps:
                st.info(f"🟡 **Medium Gaps** ({len(gaps.medium_gaps)})")
                for g in gaps.medium_gaps:
                    st.write(f"  • {g.name}: {g.percentage:.0f}%")

            if gaps.total_gap_count == 0:
                st.success("✅ No significant gaps identified! All criteria at 70% or above.")

            # Priority improvements
            priority_gaps = gaps.get_priority_gaps(3)
            if priority_gaps:
                st.markdown("---")
                st.markdown("**Priority Improvements:**")
                for i, g in enumerate(priority_gaps, 1):
                    st.write(f"{i}. **{g.name}** (Weight: {g.weight}%)")
                    st.caption(f"   Potential gain: +{g.potential_weighted_gain:.2f} weighted points")
        else:
            st.info("Gap analysis not available.")

    with tab4:
        # Detailed justifications and evidence
        st.markdown("**Detailed Justifications:**")
        for cs in score.criteria_scores:
            with st.expander(f"📝 {cs.name} ({cs.raw_score}/{cs.max_score})"):
                st.markdown("**Justification:**")
                st.write(cs.justification)
                st.markdown("**Evidence:**")
                st.write(cs.evidence)

        # Risks section
        if score.risks:
            st.markdown("---")
            st.markdown("**Identified Risks:**")
            for risk in score.risks:
                st.warning(f"⚠️ {risk}")

        # Overall summary
        st.markdown("---")
        st.markdown("**Overall Summary:**")
        st.info(score.overall_summary)

        # Relative performance
        if relative:
            st.markdown("---")
            st.markdown("**Relative Performance:**")
            col1, col2 = st.columns(2)
            with col1:
                if relative.relative_strengths:
                    st.success(f"**Strengths:** {', '.join(relative.relative_strengths)}")
            with col2:
                if relative.relative_weaknesses:
                    st.error(f"**Weaknesses:** {', '.join(relative.relative_weaknesses)}")

    with tab5:
        # Validation warnings
        warnings = supplier_result.validation_warnings if supplier_result.validation_warnings else []

        if warnings:
            st.markdown(f"**Validation Warnings** ({len(warnings)} total)")
            st.caption("These warnings indicate issues found during LLM response validation.")

            # Group warnings by type
            warning_types = {}
            for w in warnings:
                w_type = w.get('type', 'unknown')
                if w_type not in warning_types:
                    warning_types[w_type] = []
                warning_types[w_type].append(w)

            # Display by type with appropriate styling
            for w_type, type_warnings in warning_types.items():
                # Choose icon based on warning type
                icon_map = {
                    'missing_field': '📝',
                    'missing_criterion': '❓',
                    'score_adjusted': '🔧',
                    'invalid_score': '⚠️',
                    'missing_justification': '📄',
                    'missing_evidence': '🔍',
                    'duplicate_criterion': '👥',
                    'validation_error': '❌',
                    'unknown_criterion': '❔'
                }
                icon = icon_map.get(w_type, '⚠️')

                with st.expander(f"{icon} {w_type.replace('_', ' ').title()} ({len(type_warnings)})", expanded=True):
                    for w in type_warnings:
                        message = w.get('message', 'No message')
                        criterion_id = w.get('criterion_id')
                        if criterion_id:
                            st.write(f"• **Criterion {criterion_id}:** {message}")
                        else:
                            st.write(f"• {message}")

            # Impact assessment
            st.markdown("---")
            st.markdown("**Impact Assessment:**")

            critical_types = ['validation_error', 'missing_criterion', 'invalid_score']
            critical_count = sum(len(warning_types.get(t, [])) for t in critical_types)
            minor_count = len(warnings) - critical_count

            col1, col2 = st.columns(2)
            with col1:
                if critical_count > 0:
                    st.error(f"🔴 **Critical:** {critical_count} (may affect scoring)")
                else:
                    st.success("🟢 **Critical:** 0")
            with col2:
                if minor_count > 0:
                    st.warning(f"🟡 **Minor:** {minor_count} (informational)")
                else:
                    st.success("🟢 **Minor:** 0")

        else:
            st.success("✅ **No validation warnings!**")
            st.write("The LLM response passed all validation checks without any issues.")
            st.balloons()


def run_evaluation(suppliers_data: list, criteria: list) -> PipelineResult:
    """Run the evaluation pipeline with progress display."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Convert to SupplierInput objects
    supplier_inputs = []
    for s in suppliers_data:
        supplier_inputs.append(SupplierInput(
            name=s['name'],
            pdf_file=s['pdf_file'],
            metadata={
                'submission_date': s['submission_date'],
                'experience_rating': s['experience_rating']
            }
        ))

    # Create orchestrator and run
    orch = Orchestrator()

    def progress_callback(msg: str, current: int, total: int):
        if total > 0:
            progress_bar.progress(current / total)
        status_text.text(msg)

    result = orch.run(supplier_inputs, progress_callback)

    progress_bar.progress(1.0)
    status_text.text("Evaluation complete!")

    return result


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main function that runs the Streamlit app."""

    # Sidebar navigation
    st.sidebar.title("📋 RFP Evaluation")
    page = st.sidebar.radio(
        "Navigation",
        ["🏠 Home", "📤 New Evaluation", "🏆 Results", "📜 History"],
        label_visibility="collapsed"
    )

    # Show mode indicator
    mode = "🔬 MOCK MODE" if config.USE_MOCK_LLM else "🤖 LIVE MODE"
    st.sidebar.markdown(f"**Mode:** {mode}")

    # Load criteria
    try:
        criteria = get_active_criteria()
        total_weight = get_total_weight()
    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Run: `python database/init_db.py`")
        return

    # Route to pages
    if page == "🏠 Home":
        show_home_page(criteria, total_weight)
    elif page == "📤 New Evaluation":
        show_evaluation_page(criteria)
    elif page == "🏆 Results":
        show_results_page()
    elif page == "📜 History":
        show_history_page()


def show_home_page(criteria, total_weight):
    """Display the home page."""
    st.title("📋 Agentic RFP Evaluation System")
    st.markdown("---")

    st.write("""
    Welcome to the **RFP Evaluation and Supplier Ranking System**!

    This application helps you:
    - 📤 Upload supplier proposal PDFs
    - 🤖 Evaluate proposals using AI (or mock mode)
    - 📊 Score and rank suppliers automatically
    - 📁 Save and review historical evaluations
    """)

    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Criteria", len(criteria))
    with col2:
        st.metric("Total Weight", f"{total_weight}%")
    with col3:
        runs = get_all_runs()
        st.metric("Past Evaluations", len(runs))

    # Criteria overview
    st.markdown("---")
    st.subheader("📊 Evaluation Criteria")

    if criteria:
        df = pd.DataFrame(criteria)
        df = df.rename(columns={
            'criterion_id': 'ID',
            'name': 'Criterion',
            'description': 'What to Evaluate',
            'weight': 'Weight (%)',
            'max_score': 'Max Score'
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Footer
    st.markdown("---")
    st.caption("Built for IIT Roorkee - Agentic AI Mini Project")


def show_evaluation_page(criteria):
    """Display the new evaluation page."""
    st.title("📤 New Supplier Evaluation")
    st.markdown("---")

    # Initialize session state
    if 'evaluation_result' not in st.session_state:
        st.session_state.evaluation_result = None

    # Number of suppliers
    num_suppliers = st.number_input(
        "How many suppliers to evaluate?",
        min_value=1, max_value=10, value=2
    )

    st.markdown("---")

    # Collect supplier data
    suppliers_data = []
    all_valid = True

    for i in range(int(num_suppliers)):
        st.subheader(f"Supplier {i + 1}")

        col1, col2 = st.columns([2, 1])

        with col1:
            name = st.text_input(
                "Supplier Name",
                key=f"name_{i}",
                placeholder="e.g., Apex Systems"
            )

            pdf_file = st.file_uploader(
                "Upload Proposal PDF",
                type=['pdf'],
                key=f"pdf_{i}"
            )

        with col2:
            submission_date = st.date_input(
                "Submission Date",
                value=date.today(),
                key=f"date_{i}"
            )

            experience_rating = st.slider(
                "Experience Rating",
                min_value=1, max_value=10, value=5,
                key=f"exp_{i}"
            )

        # Validate
        errors = []
        extracted_text = None

        if not name:
            errors.append("Name required")
        if not pdf_file:
            errors.append("PDF required")
        else:
            try:
                is_valid, msg = validate_pdf(pdf_file)
                pdf_file.seek(0)
                if not is_valid:
                    errors.append(msg)
                else:
                    extracted_text = extract_text_from_uploaded_file(pdf_file)
                    pdf_file.seek(0)
                    pdf_info = get_pdf_info(pdf_file)
                    pdf_file.seek(0)
            except Exception as e:
                errors.append(str(e))

        if errors:
            all_valid = False
            for err in errors:
                st.warning(f"⚠️ {err}")
        else:
            st.success(f"✅ {name} - Ready")
            if pdf_info:
                st.caption(f"📄 {pdf_info['page_count']} pages | {pdf_info['char_count']:,} chars")

            suppliers_data.append({
                'name': name,
                'pdf_file': pdf_file,
                'submission_date': submission_date.strftime('%Y-%m-%d'),
                'experience_rating': experience_rating,
                'extracted_text': extracted_text
            })

        st.markdown("---")

    # Evaluate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 Run Evaluation",
            type="primary",
            disabled=not all_valid or len(suppliers_data) == 0,
            use_container_width=True
        ):
            with st.spinner("Evaluating suppliers..."):
                result = run_evaluation(suppliers_data, criteria)
                st.session_state.evaluation_result = result

                # Save to database
                run_id = save_pipeline_result(result, f"Evaluation on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                st.session_state.last_run_id = run_id

            st.success(f"✅ Evaluation complete! Run ID: {run_id}")
            st.balloons()

    # Show results if available
    if st.session_state.evaluation_result:
        st.markdown("---")
        st.header("📊 Evaluation Results")
        display_leaderboard(st.session_state.evaluation_result)

        # Detailed scorecards
        st.markdown("---")
        st.header("📋 Detailed Scorecards")

        for supplier_result in st.session_state.evaluation_result.supplier_results:
            with st.expander(f"📄 {supplier_result.supplier_name}", expanded=False):
                display_supplier_scorecard(
                    supplier_result,
                    st.session_state.evaluation_result.benchmarks
                )


def show_results_page():
    """Display the results page."""
    st.title("🏆 Evaluation Results")
    st.markdown("---")

    if 'evaluation_result' not in st.session_state or st.session_state.evaluation_result is None:
        st.info("No recent evaluation. Run a new evaluation or view history.")
        return

    result = st.session_state.evaluation_result

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Suppliers", result.total_suppliers)
    with col2:
        st.metric("Successful", result.successful_evaluations)
    with col3:
        st.metric("Failed", result.failed_evaluations)
    with col4:
        st.metric("Mode", result.evaluation_mode)

    st.markdown("---")

    # Leaderboard
    display_leaderboard(result)

    # Winner spotlight
    if result.ranking and result.ranking.rankings:
        winner = result.ranking.rankings[0]
        st.markdown("---")
        st.header("🏆 Winner Spotlight")

        winner_result = None
        for sr in result.supplier_results:
            if sr.supplier_name == winner.supplier_name:
                winner_result = sr
                break

        if winner_result:
            display_supplier_scorecard(winner_result, result.benchmarks)


def show_history_page():
    """Display evaluation history."""
    st.title("📜 Evaluation History")
    st.markdown("---")

    runs = get_all_runs()

    if not runs:
        st.info("No evaluation history yet. Run your first evaluation!")
        return

    # Display runs
    for run in runs:
        summary = get_run_summary(run['rfp_run_id'])
        if not summary:
            continue

        with st.expander(
            f"Run #{run['rfp_run_id']} - {run['created_at']} ({summary['supplier_count']} suppliers)",
            expanded=False
        ):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", summary['status'].upper())
            with col2:
                st.metric("Suppliers", summary['supplier_count'])
            with col3:
                if summary['winner']:
                    st.metric("Winner", summary['winner']['name'])

            if summary.get('results'):
                st.markdown("**Results:**")
                results_df = pd.DataFrame([
                    {
                        'Rank': r['final_rank'],
                        'Supplier': r['supplier_name'],
                        'Score': r['absolute_score'],
                        'PPI': r['ppi']
                    }
                    for r in summary['results']
                    if r['final_rank'] != 999
                ])
                if not results_df.empty:
                    st.dataframe(results_df, use_container_width=True, hide_index=True)


# =============================================================================
# RUN THE APP
# =============================================================================
if __name__ == "__main__":
    main()
