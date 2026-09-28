"""
Gaps Analysis Module

Identifies weaknesses and areas for improvement for each supplier.
Calculates gaps to thresholds, benchmarks, and potential score improvements.
All calculations are deterministic Python - no LLM involvement.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.scorer import SupplierScore, CriterionScore
from src.benchmarks import OverallBenchmarks, CriterionBenchmark


class GapSeverity(Enum):
    """Severity levels for identified gaps."""
    CRITICAL = "critical"    # Below 40% - major concern
    HIGH = "high"            # Below 60% - significant gap
    MEDIUM = "medium"        # Below 70% - moderate gap
    LOW = "low"              # Below 80% - minor gap
    NONE = "none"            # 80%+ - acceptable


@dataclass
class CriterionGap:
    """Gap analysis for a single criterion."""
    criterion_id: int
    name: str
    weight: float

    # Current scores
    score: int
    max_score: int
    percentage: float

    # Gap analysis
    severity: GapSeverity
    gap_to_threshold: float      # Points needed to reach 70%
    gap_to_benchmark_avg: float  # Points below average
    gap_to_best: float           # Points below best performer

    # Impact analysis
    potential_weighted_gain: float  # If improved to 100%
    priority_score: float           # severity * weight (for sorting)

    # Context
    benchmark_avg: Optional[float] = None
    benchmark_best: Optional[float] = None
    best_supplier: Optional[str] = None


@dataclass
class SupplierGapAnalysis:
    """Complete gap analysis for a supplier."""
    supplier_name: str
    total_score: float

    # All criterion gaps
    all_gaps: List[CriterionGap]

    # Filtered gaps by severity
    critical_gaps: List[CriterionGap] = field(default_factory=list)
    high_gaps: List[CriterionGap] = field(default_factory=list)
    medium_gaps: List[CriterionGap] = field(default_factory=list)

    # Summary
    total_gap_count: int = 0
    max_potential_improvement: float = 0.0  # If all gaps closed

    def get_priority_gaps(self, limit: int = 3) -> List[CriterionGap]:
        """Get top priority gaps to address (sorted by priority score)."""
        actionable = [g for g in self.all_gaps if g.severity != GapSeverity.NONE]
        return sorted(actionable, key=lambda g: g.priority_score, reverse=True)[:limit]


# Threshold constants
THRESHOLD_CRITICAL = 40
THRESHOLD_HIGH = 60
THRESHOLD_MEDIUM = 70
THRESHOLD_LOW = 80


def get_severity(percentage: float) -> GapSeverity:
    """Determine gap severity based on percentage score."""
    if percentage < THRESHOLD_CRITICAL:
        return GapSeverity.CRITICAL
    elif percentage < THRESHOLD_HIGH:
        return GapSeverity.HIGH
    elif percentage < THRESHOLD_MEDIUM:
        return GapSeverity.MEDIUM
    elif percentage < THRESHOLD_LOW:
        return GapSeverity.LOW
    else:
        return GapSeverity.NONE


def get_severity_weight(severity: GapSeverity) -> float:
    """Get numeric weight for severity (for priority calculation)."""
    weights = {
        GapSeverity.CRITICAL: 4.0,
        GapSeverity.HIGH: 3.0,
        GapSeverity.MEDIUM: 2.0,
        GapSeverity.LOW: 1.0,
        GapSeverity.NONE: 0.0
    }
    return weights.get(severity, 0.0)


def analyze_supplier_gaps(
    supplier_score: SupplierScore,
    benchmarks: Optional[OverallBenchmarks] = None
) -> SupplierGapAnalysis:
    """
    Analyze gaps for a single supplier.

    Args:
        supplier_score: The supplier's calculated scores
        benchmarks: Optional benchmarks for comparison

    Returns:
        SupplierGapAnalysis: Complete gap analysis

    Example:
        from src.gaps import analyze_supplier_gaps

        gap_analysis = analyze_supplier_gaps(supplier_score, benchmarks)

        print(f"Critical gaps: {len(gap_analysis.critical_gaps)}")
        for gap in gap_analysis.get_priority_gaps():
            print(f"  - {gap.name}: {gap.percentage:.0f}% ({gap.severity.value})")
    """
    all_gaps = []
    critical_gaps = []
    high_gaps = []
    medium_gaps = []
    total_potential_improvement = 0.0

    for cs in supplier_score.criteria_scores:
        # Get benchmark data if available
        benchmark = None
        benchmark_avg = None
        benchmark_best = None
        best_supplier = None

        if benchmarks:
            benchmark = benchmarks.get_benchmark_for_criterion(cs.criterion_id)
            if benchmark:
                benchmark_avg = benchmark.average_percentage
                benchmark_best = benchmark.best_percentage
                best_supplier = benchmark.best_suppliers[0] if benchmark.best_suppliers else None

        # Calculate severity
        severity = get_severity(cs.percentage)

        # Calculate gaps
        threshold_target = THRESHOLD_MEDIUM  # 70% is our target threshold
        gap_to_threshold = max(0, threshold_target - cs.percentage)

        gap_to_avg = 0.0
        if benchmark_avg is not None:
            gap_to_avg = max(0, benchmark_avg - cs.percentage)

        gap_to_best = 0.0
        if benchmark_best is not None:
            gap_to_best = max(0, benchmark_best - cs.percentage)

        # Calculate potential gain if improved to 100%
        current_weighted = (cs.percentage / 100) * cs.weight
        max_weighted = cs.weight  # 100% would give full weight
        potential_gain = max_weighted - current_weighted

        total_potential_improvement += potential_gain

        # Calculate priority score (severity weight * criterion weight)
        severity_weight = get_severity_weight(severity)
        priority_score = severity_weight * cs.weight

        gap = CriterionGap(
            criterion_id=cs.criterion_id,
            name=cs.name,
            weight=cs.weight,
            score=cs.raw_score,
            max_score=cs.max_score,
            percentage=round(cs.percentage, 2),
            severity=severity,
            gap_to_threshold=round(gap_to_threshold, 2),
            gap_to_benchmark_avg=round(gap_to_avg, 2),
            gap_to_best=round(gap_to_best, 2),
            potential_weighted_gain=round(potential_gain, 2),
            priority_score=round(priority_score, 2),
            benchmark_avg=round(benchmark_avg, 2) if benchmark_avg else None,
            benchmark_best=round(benchmark_best, 2) if benchmark_best else None,
            best_supplier=best_supplier
        )

        all_gaps.append(gap)

        # Categorize by severity
        if severity == GapSeverity.CRITICAL:
            critical_gaps.append(gap)
        elif severity == GapSeverity.HIGH:
            high_gaps.append(gap)
        elif severity == GapSeverity.MEDIUM:
            medium_gaps.append(gap)

    # Count total gaps (excluding NONE and LOW)
    total_gap_count = len(critical_gaps) + len(high_gaps) + len(medium_gaps)

    return SupplierGapAnalysis(
        supplier_name=supplier_score.supplier_name,
        total_score=round(supplier_score.total_weighted_score, 2),
        all_gaps=all_gaps,
        critical_gaps=critical_gaps,
        high_gaps=high_gaps,
        medium_gaps=medium_gaps,
        total_gap_count=total_gap_count,
        max_potential_improvement=round(total_potential_improvement, 2)
    )


def format_gap_analysis(analysis: SupplierGapAnalysis) -> str:
    """
    Format gap analysis for display.

    Args:
        analysis: The gap analysis

    Returns:
        str: Formatted output
    """
    lines = []
    lines.append("═" * 60)
    lines.append(f"GAP ANALYSIS: {analysis.supplier_name}")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Current Score: {analysis.total_score:.2f}/100")
    lines.append(f"Potential Improvement: +{analysis.max_potential_improvement:.2f} points")
    lines.append(f"Total Gaps Identified: {analysis.total_gap_count}")
    lines.append("")

    # Show critical gaps
    if analysis.critical_gaps:
        lines.append("🔴 CRITICAL GAPS (below 40%):")
        for gap in analysis.critical_gaps:
            lines.append(f"   • {gap.name}: {gap.score}/{gap.max_score} ({gap.percentage:.0f}%)")
            lines.append(f"     Need +{gap.gap_to_threshold:.0f}% to reach threshold")
        lines.append("")

    # Show high gaps
    if analysis.high_gaps:
        lines.append("🟠 HIGH GAPS (40-60%):")
        for gap in analysis.high_gaps:
            lines.append(f"   • {gap.name}: {gap.score}/{gap.max_score} ({gap.percentage:.0f}%)")
            lines.append(f"     Need +{gap.gap_to_threshold:.0f}% to reach threshold")
        lines.append("")

    # Show medium gaps
    if analysis.medium_gaps:
        lines.append("🟡 MEDIUM GAPS (60-70%):")
        for gap in analysis.medium_gaps:
            lines.append(f"   • {gap.name}: {gap.score}/{gap.max_score} ({gap.percentage:.0f}%)")
        lines.append("")

    # Priority recommendations
    priority_gaps = analysis.get_priority_gaps(3)
    if priority_gaps:
        lines.append("📋 TOP PRIORITY IMPROVEMENTS:")
        for i, gap in enumerate(priority_gaps, 1):
            lines.append(f"   {i}. {gap.name} (Weight: {gap.weight}%)")
            lines.append(f"      Current: {gap.percentage:.0f}% → Target: 70%+")
            lines.append(f"      Potential gain: +{gap.potential_weighted_gain:.2f} weighted points")
        lines.append("")

    # No gaps message
    if analysis.total_gap_count == 0:
        lines.append("✅ No significant gaps identified!")
        lines.append("   All criteria are at 70% or above.")
        lines.append("")

    lines.append("═" * 60)

    return "\n".join(lines)


def get_all_supplier_gaps(
    scores: List[SupplierScore],
    benchmarks: Optional[OverallBenchmarks] = None
) -> List[SupplierGapAnalysis]:
    """
    Analyze gaps for all suppliers.

    Args:
        scores: List of supplier scores
        benchmarks: Optional benchmarks for comparison

    Returns:
        List of gap analyses, sorted by total gap count (most gaps first)
    """
    analyses = []
    for score in scores:
        analysis = analyze_supplier_gaps(score, benchmarks)
        analyses.append(analysis)

    # Sort by gap count (most gaps first)
    return sorted(analyses, key=lambda a: a.total_gap_count, reverse=True)


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score
    from src.benchmarks import compute_benchmarks

    print("=== Testing Gap Analysis ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    # Create mock suppliers with varying quality
    sample_proposals = [
        ("Strong Corp", "Enterprise leader with 20 years experience. Full SOC 2 and ISO 27001. Premium 24/7 support. Competitive pricing at $400,000. Modern architecture."),
        ("Average Inc", "Standard solution with basic features. 5 years experience. Basic security. Email support only. Mid-range pricing."),
        ("Weak Ltd", "New company, limited experience. No certifications yet. Basic support during business hours only."),
    ]

    print("Evaluating suppliers...")
    scores = []
    for name, proposal in sample_proposals:
        raw = evaluator.evaluate(proposal, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)
        print(f"  {name}: {score.total_weighted_score:.2f}/100")

    print()

    # Compute benchmarks
    benchmarks = compute_benchmarks(scores)

    # Analyze gaps for each supplier
    print("Analyzing gaps...")
    print()

    for score in scores:
        analysis = analyze_supplier_gaps(score, benchmarks)
        print(format_gap_analysis(analysis))
        print()
