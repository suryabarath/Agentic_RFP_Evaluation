"""
PPI (Proposal Performance Index) Module

Calculates a composite performance index that considers:
1. Weighted Score (primary factor)
2. Consistency (low variance across criteria is rewarded)
3. Risk Penalty (identified risks reduce score)
4. Validation Quality (warnings indicate data quality issues)

All calculations are deterministic Python - no LLM involvement.

PPI Formula:
    PPI = (WeightedScore * 0.70) + (ConsistencyBonus * 0.15) + (QualityBonus * 0.15) - RiskPenalty
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import statistics
import math

from src.scorer import SupplierScore


# PPI Configuration
PPI_WEIGHTS = {
    'weighted_score': 0.70,    # 70% from raw weighted score
    'consistency': 0.15,       # 15% from consistency bonus
    'quality': 0.15,           # 15% from quality bonus
}

RISK_PENALTY_PER_RISK = 1.0    # Points deducted per risk
WARNING_PENALTY = 0.5          # Points deducted per warning
MAX_RISK_PENALTY = 10.0        # Cap on risk penalty
MAX_WARNING_PENALTY = 5.0      # Cap on warning penalty


@dataclass
class PPIBreakdown:
    """Detailed breakdown of PPI calculation."""
    supplier_name: str

    # Input values
    weighted_score: float
    risk_count: int
    warning_count: int

    # Calculated components
    consistency_score: float      # 0-100 (100 = perfectly consistent)
    consistency_bonus: float      # Contribution to PPI

    quality_score: float          # 0-100 (100 = no warnings)
    quality_bonus: float          # Contribution to PPI

    risk_penalty: float           # Deduction for risks

    # Final PPI
    ppi_score: float              # Final composite index (0-100)

    # Component contributions
    weighted_contribution: float  # Points from weighted score
    consistency_contribution: float
    quality_contribution: float

    # Interpretation
    ppi_grade: str               # A, B, C, D, F


def calculate_consistency_score(score: SupplierScore) -> float:
    """
    Calculate consistency score based on variance in criterion percentages.

    A supplier with consistent scores across all criteria gets a higher
    consistency score than one with high variance.

    Returns:
        float: Consistency score 0-100 (100 = perfectly consistent)
    """
    if not score.criteria_scores:
        return 100.0

    percentages = [cs.percentage for cs in score.criteria_scores]

    if len(percentages) < 2:
        return 100.0

    # Calculate coefficient of variation (CV)
    mean_pct = statistics.mean(percentages)
    if mean_pct == 0:
        return 0.0

    std_dev = statistics.stdev(percentages)
    cv = (std_dev / mean_pct) * 100  # CV as percentage

    # Convert CV to consistency score
    # CV of 0 = 100% consistent
    # CV of 50+ = 0% consistent
    # Linear scale in between
    consistency = max(0, 100 - (cv * 2))

    return round(consistency, 2)


def calculate_quality_score(warning_count: int) -> float:
    """
    Calculate quality score based on validation warnings.

    Returns:
        float: Quality score 0-100 (100 = no warnings)
    """
    if warning_count == 0:
        return 100.0

    # Each warning reduces quality by 10%, minimum 0
    quality = max(0, 100 - (warning_count * 10))
    return round(quality, 2)


def get_ppi_grade(ppi: float) -> str:
    """Convert PPI score to letter grade."""
    if ppi >= 90:
        return "A"
    elif ppi >= 80:
        return "B"
    elif ppi >= 70:
        return "C"
    elif ppi >= 60:
        return "D"
    else:
        return "F"


def calculate_ppi(score: SupplierScore) -> PPIBreakdown:
    """
    Calculate the Proposal Performance Index for a supplier.

    Args:
        score: The supplier's calculated scores

    Returns:
        PPIBreakdown: Detailed PPI breakdown

    Example:
        from src.ppi import calculate_ppi

        ppi = calculate_ppi(supplier_score)
        print(f"{ppi.supplier_name}: PPI = {ppi.ppi_score:.2f} (Grade: {ppi.ppi_grade})")
    """
    # Get input values
    weighted_score = score.total_weighted_score
    risk_count = len(score.risks)
    warning_count = score.warnings_count

    # Calculate consistency
    consistency_score = calculate_consistency_score(score)
    consistency_bonus = (consistency_score / 100) * 100  # Scale to 0-100

    # Calculate quality
    quality_score = calculate_quality_score(warning_count)
    quality_bonus = quality_score  # Already 0-100

    # Calculate risk penalty
    risk_penalty = min(risk_count * RISK_PENALTY_PER_RISK, MAX_RISK_PENALTY)
    warning_penalty = min(warning_count * WARNING_PENALTY, MAX_WARNING_PENALTY)
    total_penalty = risk_penalty + warning_penalty

    # Calculate contributions
    weighted_contribution = weighted_score * PPI_WEIGHTS['weighted_score']
    consistency_contribution = consistency_bonus * PPI_WEIGHTS['consistency']
    quality_contribution = quality_bonus * PPI_WEIGHTS['quality']

    # Calculate final PPI
    ppi_raw = weighted_contribution + consistency_contribution + quality_contribution - total_penalty

    # Clamp to 0-100
    ppi_score = max(0, min(100, ppi_raw))

    # Get grade
    ppi_grade = get_ppi_grade(ppi_score)

    return PPIBreakdown(
        supplier_name=score.supplier_name,
        weighted_score=round(weighted_score, 2),
        risk_count=risk_count,
        warning_count=warning_count,
        consistency_score=consistency_score,
        consistency_bonus=round(consistency_bonus, 2),
        quality_score=quality_score,
        quality_bonus=round(quality_bonus, 2),
        risk_penalty=round(total_penalty, 2),
        ppi_score=round(ppi_score, 2),
        weighted_contribution=round(weighted_contribution, 2),
        consistency_contribution=round(consistency_contribution, 2),
        quality_contribution=round(quality_contribution, 2),
        ppi_grade=ppi_grade
    )


def calculate_all_ppi(scores: List[SupplierScore]) -> List[PPIBreakdown]:
    """
    Calculate PPI for all suppliers.

    Args:
        scores: List of supplier scores

    Returns:
        List of PPI breakdowns, sorted by PPI score (highest first)
    """
    ppis = [calculate_ppi(score) for score in scores]
    return sorted(ppis, key=lambda p: p.ppi_score, reverse=True)


def format_ppi_breakdown(ppi: PPIBreakdown) -> str:
    """
    Format PPI breakdown for display.

    Args:
        ppi: The PPI breakdown

    Returns:
        str: Formatted output
    """
    grade_emoji = {
        'A': '🌟',
        'B': '✅',
        'C': '⚡',
        'D': '⚠️',
        'F': '❌'
    }

    lines = []
    lines.append("═" * 60)
    lines.append(f"PPI BREAKDOWN: {ppi.supplier_name}")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"PPI SCORE: {ppi.ppi_score:.2f}/100 {grade_emoji.get(ppi.ppi_grade, '')} Grade: {ppi.ppi_grade}")
    lines.append("")
    lines.append("COMPONENT BREAKDOWN:")
    lines.append("-" * 40)
    lines.append(f"  Weighted Score ({PPI_WEIGHTS['weighted_score']*100:.0f}%):")
    lines.append(f"    Base: {ppi.weighted_score:.2f}/100")
    lines.append(f"    Contribution: +{ppi.weighted_contribution:.2f}")
    lines.append("")
    lines.append(f"  Consistency ({PPI_WEIGHTS['consistency']*100:.0f}%):")
    lines.append(f"    Score: {ppi.consistency_score:.1f}/100")
    lines.append(f"    Contribution: +{ppi.consistency_contribution:.2f}")
    lines.append("")
    lines.append(f"  Quality ({PPI_WEIGHTS['quality']*100:.0f}%):")
    lines.append(f"    Score: {ppi.quality_score:.1f}/100 ({ppi.warning_count} warnings)")
    lines.append(f"    Contribution: +{ppi.quality_contribution:.2f}")
    lines.append("")
    lines.append(f"  Risk Penalty:")
    lines.append(f"    Risks: {ppi.risk_count}")
    lines.append(f"    Penalty: -{ppi.risk_penalty:.2f}")
    lines.append("")
    lines.append("CALCULATION:")
    lines.append(f"  {ppi.weighted_contribution:.2f} + {ppi.consistency_contribution:.2f} + {ppi.quality_contribution:.2f} - {ppi.risk_penalty:.2f} = {ppi.ppi_score:.2f}")
    lines.append("")
    lines.append("═" * 60)

    return "\n".join(lines)


def format_ppi_comparison(ppis: List[PPIBreakdown]) -> str:
    """
    Format PPI comparison table.

    Args:
        ppis: List of PPI breakdowns (sorted by PPI score)

    Returns:
        str: Formatted comparison table
    """
    lines = []
    lines.append("═" * 70)
    lines.append("PPI COMPARISON")
    lines.append("═" * 70)
    lines.append("")
    lines.append(f"{'Rank':<5} {'Supplier':<20} {'Weighted':<10} {'Consist.':<10} {'Quality':<10} {'PPI':<8} {'Grade'}")
    lines.append("-" * 70)

    for rank, ppi in enumerate(ppis, 1):
        lines.append(
            f"#{rank:<4} {ppi.supplier_name:<20} "
            f"{ppi.weighted_score:<10.2f} "
            f"{ppi.consistency_score:<10.1f} "
            f"{ppi.quality_score:<10.1f} "
            f"{ppi.ppi_score:<8.2f} "
            f"{ppi.ppi_grade}"
        )

    lines.append("")
    lines.append("Legend: Weighted=Base Score, Consist.=Consistency, Quality=Data Quality")
    lines.append("═" * 70)

    return "\n".join(lines)


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score

    print("=== Testing PPI Calculation ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    # Create mock suppliers
    sample_proposals = [
        ("Consistent Corp", "We excel in all areas: technical capability, implementation, pricing, security, and support. Balanced approach across all criteria."),
        ("Specialist Inc", "World-class security with SOC 2 Type II, ISO 27001, and FedRAMP. Other areas are adequate but security is our focus."),
        ("Budget Ltd", "Affordable solution at lowest price point. Basic features. Limited support. Minimal security certifications."),
    ]

    print("Evaluating suppliers...")
    scores = []
    for name, proposal in sample_proposals:
        raw = evaluator.evaluate(proposal, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)
        print(f"  {name}: Weighted={score.total_weighted_score:.2f}, Risks={len(score.risks)}, Warnings={score.warnings_count}")

    print()

    # Calculate PPI for all
    ppis = calculate_all_ppi(scores)

    # Show comparison
    print(format_ppi_comparison(ppis))
    print()

    # Show detailed breakdown for top performer
    print("Detailed breakdown for top PPI:")
    print(format_ppi_breakdown(ppis[0]))
