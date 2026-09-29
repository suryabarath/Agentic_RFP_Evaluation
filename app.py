"""
Agentic RFP Evaluation and Supplier Ranking

This is the main Streamlit application file.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import json
from datetime import date, datetime

# Import our modules
from src.database import (
    get_active_criteria, get_total_weight, save_pipeline_result,
    get_all_runs, get_run_summary
)
from src.pdf_tool import extract_text_from_uploaded_file, get_pdf_info, validate_pdf
from src.evaluator import evaluator
from src.orchestrator import Orchestrator, SupplierInput, PipelineResult
from src.config import config, PROVIDERS
from src.export import export_full_report, export_summary, export_supplier_scorecard, to_json_string

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="RFP Evaluation System",
    page_icon="📋",
    layout="wide"
)

# =============================================================================
# CUSTOM CSS STYLING
# =============================================================================
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Header styling */
    h1 {
        color: #1e293b;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        color: #334155;
        font-weight: 600;
    }

    /* Card styling for metrics and info boxes */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* Styled container */
    .styled-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .status-success {
        background-color: #d1fae5;
        color: #065f46;
    }

    .status-warning {
        background-color: #fef3c7;
        color: #92400e;
    }

    .status-error {
        background-color: #fee2e2;
        color: #991b1b;
    }

    /* Rank badges */
    .rank-1 {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }

    .rank-2 {
        background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }

    .rank-3 {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }

    /* Score display */
    .score-display {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e293b;
    }

    .score-label {
        font-size: 0.875rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
    }

    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #1e293b;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* DataFrames */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #334155;
    }

    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }

    /* File uploader */
    .stFileUploader {
        border-radius: 8px;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        color: #64748b;
    }

    /* Divider */
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #e2e8f0, transparent);
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #64748b;
        font-size: 0.875rem;
    }

    /* Hero section */
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 2rem;
        color: white;
        margin-bottom: 2rem;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
    }

    /* Feature cards */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        height: 100%;
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }

    .feature-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }

    .feature-desc {
        font-size: 0.9rem;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# AI CONFIGURATION SIDEBAR
# =============================================================================

def render_ai_config_sidebar():
    """Render the AI Configuration section in the sidebar."""

    # Initialize session state for AI config
    if 'ai_offline_mode' not in st.session_state:
        st.session_state.ai_offline_mode = config.USE_MOCK_LLM
    if 'ai_provider' not in st.session_state:
        st.session_state.ai_provider = config.PROVIDER
    if 'ai_model' not in st.session_state:
        st.session_state.ai_model = config.MODEL
    if 'ai_api_key' not in st.session_state:
        st.session_state.ai_api_key = config.get_api_key()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### :gear: AI Configuration")

    # Offline mode checkbox
    offline_mode = st.sidebar.checkbox(
        "Offline demo mode (no API key, no cost)",
        value=st.session_state.ai_offline_mode,
        help="Enable this for testing without an API key. Uses simulated evaluations."
    )

    # Update session state and config
    if offline_mode != st.session_state.ai_offline_mode:
        st.session_state.ai_offline_mode = offline_mode
        config.set_runtime_config(use_mock=offline_mode)
        evaluator.reset_clients()

    # Mode indicator box
    if offline_mode:
        st.sidebar.markdown("""
        <div style="border-left: 4px solid #94a3b8; padding: 12px 14px; background-color: #f8f9fa; margin: 10px 0; border-radius: 0 8px 8px 0;">
            <span style="color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">MODE</span><br>
            <div style="display: flex; align-items: center; margin-top: 4px;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #94a3b8; border-radius: 50%; margin-right: 8px;"></span>
                <span style="font-size: 16px; font-weight: 600; color: #1e293b;">Offline Mode</span>
            </div>
            <span style="color: #64748b; font-size: 13px; margin-top: 2px; display: block;">Uses simulated mock evaluations.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""
        <div style="border-left: 4px solid #22c55e; padding: 12px 14px; background-color: #f0fdf4; margin: 10px 0; border-radius: 0 8px 8px 0;">
            <span style="color: #16a34a; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">MODE</span><br>
            <div style="display: flex; align-items: center; margin-top: 4px;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #22c55e; border-radius: 50%; margin-right: 8px; box-shadow: 0 0 6px #22c55e;"></span>
                <span style="font-size: 16px; font-weight: 600; color: #1e293b;">Live Mode</span>
            </div>
            <span style="color: #16a34a; font-size: 13px; margin-top: 2px; display: block;">Calls a real LLM with your key.</span>
        </div>
        """, unsafe_allow_html=True)

        # Provider selection
        provider_names = {k: v['name'] for k, v in PROVIDERS.items()}
        provider_options = list(provider_names.keys())
        provider_labels = list(provider_names.values())

        current_provider_idx = provider_options.index(st.session_state.ai_provider) if st.session_state.ai_provider in provider_options else 0

        selected_provider_label = st.sidebar.selectbox(
            "Provider",
            options=provider_labels,
            index=current_provider_idx
        )

        # Get provider key from label
        selected_provider = provider_options[provider_labels.index(selected_provider_label)]

        # Update if provider changed
        if selected_provider != st.session_state.ai_provider:
            st.session_state.ai_provider = selected_provider
            # Set default model for new provider
            st.session_state.ai_model = PROVIDERS[selected_provider]['default_model']
            config.set_runtime_config(provider=selected_provider, model=st.session_state.ai_model)
            evaluator.reset_clients()
            st.rerun()

        # Model input
        provider_models = PROVIDERS.get(selected_provider, {}).get('models', [])
        model = st.sidebar.selectbox(
            "Model",
            options=provider_models,
            index=provider_models.index(st.session_state.ai_model) if st.session_state.ai_model in provider_models else 0
        )

        if model != st.session_state.ai_model:
            st.session_state.ai_model = model
            config.set_runtime_config(model=model)

        # API Key input
        api_key = st.sidebar.text_input(
            "API Key",
            value=st.session_state.ai_api_key,
            type="password",
            help=f"Your {selected_provider_label} API key. Get one from the provider's website."
        )

        if api_key != st.session_state.ai_api_key:
            st.session_state.ai_api_key = api_key
            config.set_runtime_config(api_key=api_key)
            evaluator.reset_clients()

        # Test Connection button
        if st.sidebar.button(":zap: Test Connection", use_container_width=True):
            with st.sidebar:
                with st.spinner("Testing connection..."):
                    success, message = evaluator.test_connection()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


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

    st.markdown("### 🏆 Final Ranking")

    # Show winner card if available
    if result.ranking.rankings:
        winner = result.ranking.rankings[0]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); border-radius: 12px; padding: 1.5rem; color: white; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.875rem; opacity: 0.9;">WINNER</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{winner.supplier_name}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2rem; font-weight: 700;">{winner.weighted_score:.1f}</div>
                    <div style="font-size: 0.875rem; opacity: 0.9;">Score</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Create leaderboard dataframe
    leaderboard_data = []
    for r in result.ranking.rankings:
        rank_display = f"#{r.rank}"
        if r.rank == 1:
            rank_display = "🥇 #1"
        elif r.rank == 2:
            rank_display = "🥈 #2"
        elif r.rank == 3:
            rank_display = "🥉 #3"

        leaderboard_data.append({
            'Rank': rank_display,
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
            st.markdown(f"##### 📝 {cs.name} ({cs.raw_score}/{cs.max_score})")
            st.markdown("**Justification:**")
            st.write(cs.justification)
            st.markdown("**Evidence:**")
            st.write(cs.evidence)
            st.markdown("---")

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

    # Render AI Configuration sidebar
    render_ai_config_sidebar()

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

    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">Agentic RFP Evaluation System</div>
        <div class="hero-subtitle">AI-powered supplier proposal evaluation and ranking platform</div>
    </div>
    """, unsafe_allow_html=True)

    # Feature Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📤</div>
            <div class="feature-title">Upload PDFs</div>
            <div class="feature-desc">Upload supplier proposal documents for analysis</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI Analysis</div>
            <div class="feature-desc">Evaluate proposals using advanced LLM technology</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Smart Scoring</div>
            <div class="feature-desc">Automatic scoring with weighted criteria</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🏆</div>
            <div class="feature-title">Rankings</div>
            <div class="feature-desc">Compare and rank suppliers objectively</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Stats
    runs = get_all_runs()

    st.markdown("### Quick Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Criteria", len(criteria), help="Number of evaluation criteria configured")
    with col2:
        st.metric("Total Weight", f"{total_weight}%", help="Sum of all criteria weights")
    with col3:
        st.metric("Past Evaluations", len(runs), help="Number of completed evaluation runs")

    # Criteria overview
    st.markdown("---")
    st.markdown("### Evaluation Criteria")
    st.caption("Proposals are evaluated against these weighted criteria")

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

    # Getting Started
    st.markdown("---")
    st.markdown("### Getting Started")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-card">
            <strong>Step 1: Configure AI</strong><br>
            <span style="color: #64748b;">Choose between Offline (demo) mode or Live mode with your API key in the sidebar.</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card">
            <strong>Step 2: Start Evaluation</strong><br>
            <span style="color: #64748b;">Go to "New Evaluation" to upload supplier PDFs and run the analysis.</span>
        </div>
        """, unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        Built for <strong>IIT Roorkee</strong> • Agentic AI Mini Project
    </div>
    """, unsafe_allow_html=True)


def show_evaluation_page(criteria):
    """Display the new evaluation page."""
    st.markdown("## 📤 New Supplier Evaluation")
    st.caption("Upload supplier proposals and run AI-powered evaluation")
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
    st.markdown("## 🏆 Evaluation Results")
    st.caption("View detailed results from the most recent evaluation")
    st.markdown("---")

    if 'evaluation_result' not in st.session_state or st.session_state.evaluation_result is None:
        st.markdown("""
        <div class="info-card" style="text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
            <strong>No Recent Evaluation</strong><br>
            <span style="color: #64748b;">Run a new evaluation or view history to see results.</span>
        </div>
        """, unsafe_allow_html=True)
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

    # Export buttons
    st.markdown("---")
    st.subheader("📥 Export Results")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Full report export
        full_report = export_full_report(result)
        full_json = to_json_string(full_report)
        st.download_button(
            label="📄 Full Report (JSON)",
            data=full_json,
            file_name=f"rfp_evaluation_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        # Summary export
        summary = export_summary(result)
        summary_json = to_json_string(summary)
        st.download_button(
            label="📋 Summary (JSON)",
            data=summary_json,
            file_name=f"rfp_evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        # CSV export of rankings
        if result.ranking and result.ranking.rankings:
            rankings_data = [
                {
                    "Rank": r.rank,
                    "Supplier": r.supplier_name,
                    "Score": r.weighted_score,
                    "PPI": r.ppi_score,
                    "Risks": r.risk_count,
                    "Warnings": r.warning_count
                }
                for r in result.ranking.rankings
            ]
            rankings_df = pd.DataFrame(rankings_data)
            csv_data = rankings_df.to_csv(index=False)
            st.download_button(
                label="📊 Rankings (CSV)",
                data=csv_data,
                file_name=f"rfp_rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

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

    # Individual supplier exports
    st.markdown("---")
    st.subheader("📥 Export Individual Scorecards")
    for sr in result.supplier_results:
        if sr.success:
            scorecard = export_supplier_scorecard(sr)
            scorecard_json = to_json_string(scorecard)
            st.download_button(
                label=f"📄 {sr.supplier_name}",
                data=scorecard_json,
                file_name=f"scorecard_{sr.supplier_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key=f"export_{sr.supplier_name}"
            )


def show_history_page():
    """Display evaluation history."""
    st.markdown("## 📜 Evaluation History")
    st.caption("View all past evaluation runs and their results")
    st.markdown("---")

    runs = get_all_runs()

    if not runs:
        st.markdown("""
        <div class="info-card" style="text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📁</div>
            <strong>No History Yet</strong><br>
            <span style="color: #64748b;">Run your first evaluation to see it here.</span>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"**{len(runs)} evaluation(s) found**")

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
