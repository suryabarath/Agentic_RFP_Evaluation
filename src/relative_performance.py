"""
Relative Performance Module

Calculates how each supplier performs relative to others in the pool.
Includes percentile ranking, normalized scores, and comparative metrics.
All calculations are deterministic Python - no LLM involvement.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.scorer import SupplierScore


class PerformanceTier(Enum):
    """Performance tier based on percentile ranking."""
    TOP = "top"           # Top 25%
    ABOVE_AVG = "above_average"  # 50-75%
    AVERAGE = "average"   # 25-50%
    BELOW_AVG = "below_average"  # Bottom 25%


@dataclass
class CriterionRelativeScore:
    """Relative performance for a single criterion."""
    criterion_id: int
    name: str

    # Absolute scores
    score: int
    max_score: int
    percentage: float

    # Relative metrics
    rank: int                    # 1 = best
    percentile: float            # 0-100, higher is better
    normalized_score: float      # Score relative to best (best = 100)
    distance_from_best: float    # Percentage points below best
    distance_from_avg: float     # Percentage points from average


@dataclass
class SupplierRelativePerformance:
    """Complete relative performance analysis for a supplier."""
    supplier_name: str

    # Overall metrics
    total_weighted_score: float
    rank: int                      # 1 = best overall
    total_suppliers: int
    percentile: float              # 0-100, higher is better
    tier: PerformanceTier

    # Normalized metrics
    normalized_score: float        # Relative to best (best = 100)
    distance_from_leader: float    # Points behind #1
    distance_from_avg: float       # Points from average

    # Per-criterion relative scores
    criteria_relative: List[CriterionRelativeScore]

    # Strengths and weaknesses (relative to pool)
    relative_strengths: List[str] = field(default_factory=list)  # Criteria where above avg
    relative_weaknesses: List[str] = field(default_factory=list)  # Criteria where below avg


def calculate_percentile(rank: int, total: int) -> float:
    """
    Calculate percentile from rank.

    Percentile = (total - rank + 1) / total * 100
    Rank 1 out of 4 = 100th percentile (top)
    Rank 4 out of 4 = 25th percentile (bottom)
    """
    if total == 0:
        return 0.0
    return ((total - rank + 1) / total) * 100


def get_tier(percentile: float) -> PerformanceTier:
    """Determine performance tier from percentile."""
    if percentile >= 75:
        return PerformanceTier.TOP
    elif percentile >= 50:
        return PerformanceTier.ABOVE_AVG
    elif percentile >= 25:
        return PerformanceTier.AVERAGE
    else:
        return PerformanceTier.BELOW_AVG


def calculate_relative_performance(
    scores: List[SupplierScore]
) -> List[SupplierRelativePerformance]:
    """
    Calculate relative performance for all suppliers.

    Args:
        scores: List of supplier scores

    Returns:
        List of relative performance analyses, sorted by rank (best first)

    Example:
        from src.relative_performance import calculate_relative_performance

        relative = calculate_relative_performance(scores)

        for r in relative:
            print(f"#{r.rank} {r.supplier_name}: {r.percentile:.0f}th percentile")
    """
    if not scores:
        return []

    total_suppliers = len(scores)

    # Sort by total weighted score (descending) for overall ranking
    sorted_scores = sorted(
        scores,
        key=lambda s: s.total_weighted_score,
        reverse=True
    )

    # Get best score and average for normalization
    best_total = sorted_scores[0].total_weighted_score
    avg_total = sum(s.total_weighted_score for s in scores) / total_suppliers

    # Build criterion-level rankings
    # For each criterion, rank all suppliers
    criterion_rankings = _build_criterion_rankings(scores)

    # Calculate relative performance for each supplier
    results = []

    for rank, supplier_score in enumerate(sorted_scores, 1):
        # Overall percentile
        percentile = calculate_percentile(rank, total_suppliers)
        tier = get_tier(percentile)

        # Normalized score (relative to best)
        if best_total > 0:
            normalized = (supplier_score.total_weighted_score / best_total) * 100
        else:
            normalized = 0.0

        distance_from_leader = best_total - supplier_score.total_weighted_score
        distance_from_avg = supplier_score.total_weighted_score - avg_total

        # Per-criterion relative scores
        criteria_relative = []
        relative_strengths = []
        relative_weaknesses = []

        for cs in supplier_score.criteria_scores:
            cid = cs.criterion_id
            criterion_data = criterion_rankings.get(cid, {})

            # Get rank for this criterion
            criterion_rank = criterion_data.get('ranks', {}).get(supplier_score.supplier_name, 1)
            criterion_percentile = calculate_percentile(criterion_rank, total_suppliers)

            # Get best and average for this criterion
            criterion_best_pct = criterion_data.get('best_percentage', 100)
            criterion_avg_pct = criterion_data.get('avg_percentage', 50)

            # Normalized score for criterion
            if criterion_best_pct > 0:
                criterion_normalized = (cs.percentage / criterion_best_pct) * 100
            else:
                criterion_normalized = 0.0

            distance_from_criterion_best = criterion_best_pct - cs.percentage
            distance_from_criterion_avg = cs.percentage - criterion_avg_pct

            criteria_relative.append(CriterionRelativeScore(
                criterion_id=cid,
                name=cs.name,
                score=cs.raw_score,
                max_score=cs.max_score,
                percentage=round(cs.percentage, 2),
                rank=criterion_rank,
                percentile=round(criterion_percentile, 2),
                normalized_score=round(criterion_normalized, 2),
                distance_from_best=round(distance_from_criterion_best, 2),
                distance_from_avg=round(distance_from_criterion_avg, 2)
            ))

            # Identify strengths and weaknesses
            if distance_from_criterion_avg > 5:
                relative_strengths.append(cs.name)
            elif distance_from_criterion_avg < -5:
                relative_weaknesses.append(cs.name)

        results.append(SupplierRelativePerformance(
            supplier_name=supplier_score.supplier_name,
            total_weighted_score=round(supplier_score.total_weighted_score, 2),
            rank=rank,
            total_suppliers=total_suppliers,
            percentile=round(percentile, 2),
            tier=tier,
            normalized_score=round(normalized, 2),
            distance_from_leader=round(distance_from_leader, 2),
            distance_from_avg=round(distance_from_avg, 2),
            criteria_relative=criteria_relative,
            relative_strengths=relative_strengths,
            relative_weaknesses=relative_weaknesses
        ))

    return results


def _build_criterion_rankings(scores: List[SupplierScore]) -> Dict[int, Dict[str, Any]]:
    """Build rankings for each criterion across all suppliers."""
    if not scores:
        return {}

    # Get all criterion IDs
    criterion_ids = [cs.criterion_id for cs in scores[0].criteria_scores]

    rankings = {}

    for cid in criterion_ids:
        # Collect scores for this criterion
        criterion_scores = []
        for supplier_score in scores:
            for cs in supplier_score.criteria_scores:
                if cs.criterion_id == cid:
                    criterion_scores.append({
                        'supplier': supplier_score.supplier_name,
                        'percentage': cs.percentage
                    })
                    break

        # Sort by percentage (descending)
        criterion_scores.sort(key=lambda x: x['percentage'], reverse=True)

        # Build rank mapping
        ranks = {}
        for rank, item in enumerate(criterion_scores, 1):
            ranks[item['supplier']] = rank

        # Calculate best and average
        percentages = [x['percentage'] for x in criterion_scores]
        best_pct = max(percentages) if percentages else 0
        avg_pct = sum(percentages) / len(percentages) if percentages else 0

        rankings[cid] = {
            'ranks': ranks,
            'best_percentage': best_pct,
            'avg_percentage': avg_pct
        }

    return rankings


def format_relative_performance(perf: SupplierRelativePerformance) -> str:
    """
    Format relative performance for display.

    Args:
        perf: The relative performance analysis

    Returns:
        str: Formatted output
    """
    tier_emoji = {
        PerformanceTier.TOP: "🥇",
        PerformanceTier.ABOVE_AVG: "🥈",
        PerformanceTier.AVERAGE: "🥉",
        PerformanceTier.BELOW_AVG: "📉"
    }

    lines = []
    lines.append("═" * 60)
    lines.append(f"RELATIVE PERFORMANCE: {perf.supplier_name}")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Overall Rank: #{perf.rank} of {perf.total_suppliers}")
    lines.append(f"Percentile: {perf.percentile:.0f}th")
    lines.append(f"Tier: {tier_emoji.get(perf.tier, '')} {perf.tier.value.replace('_', ' ').title()}")
    lines.append("")
    lines.append(f"Score: {perf.total_weighted_score:.2f}/100")
    lines.append(f"Normalized Score: {perf.normalized_score:.1f} (best = 100)")

    if perf.rank > 1:
        lines.append(f"Distance from Leader: -{perf.distance_from_leader:.2f} points")
    else:
        lines.append(f"Distance from Leader: 0 (IS THE LEADER)")

    if perf.distance_from_avg >= 0:
        lines.append(f"Distance from Average: +{perf.distance_from_avg:.2f} points")
    else:
        lines.append(f"Distance from Average: {perf.distance_from_avg:.2f} points")

    lines.append("")
    lines.append("PER-CRITERION RANKING:")
    lines.append("-" * 40)

    for cr in perf.criteria_relative:
        rank_str = f"#{cr.rank}"
        if cr.rank == 1:
            rank_str = "#1 🏆"
        lines.append(f"  {cr.name}: {rank_str} ({cr.percentile:.0f}th %ile)")
        lines.append(f"    Score: {cr.score}/{cr.max_score} ({cr.percentage:.0f}%)")

    lines.append("")

    if perf.relative_strengths:
        lines.append(f"Relative Strengths: {', '.join(perf.relative_strengths)}")
    if perf.relative_weaknesses:
        lines.append(f"Relative Weaknesses: {', '.join(perf.relative_weaknesses)}")

    lines.append("")
    lines.append("═" * 60)

    return "\n".join(lines)


def format_leaderboard(performances: List[SupplierRelativePerformance]) -> str:
    """
    Format a leaderboard showing all suppliers.

    Args:
        performances: List of relative performances (already sorted by rank)

    Returns:
        str: Formatted leaderboard
    """
    lines = []
    lines.append("═" * 60)
    lines.append("SUPPLIER LEADERBOARD")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"{'Rank':<6} {'Supplier':<25} {'Score':<10} {'%ile':<8} {'Tier'}")
    lines.append("-" * 60)

    tier_emoji = {
        PerformanceTier.TOP: "🥇",
        PerformanceTier.ABOVE_AVG: "🥈",
        PerformanceTier.AVERAGE: "🥉",
        PerformanceTier.BELOW_AVG: "📉"
    }

    for perf in performances:
        emoji = tier_emoji.get(perf.tier, "")
        lines.append(
            f"#{perf.rank:<5} {perf.supplier_name:<25} "
            f"{perf.total_weighted_score:<10.2f} "
            f"{perf.percentile:<8.0f} "
            f"{emoji}"
        )

    lines.append("")
    lines.append("═" * 60)

    return "\n".join(lines)


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score

    print("=== Testing Relative Performance ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    # Create 4 mock suppliers with varying quality
    sample_proposals = [
        ("Alpha Corp", "Enterprise leader with 20 years experience. SOC 2 and ISO 27001 certified. Premium 24/7 support. Competitive pricing."),
        ("Beta Inc", "Innovative startup with modern architecture. 5 years experience. Good security practices. Competitive pricing."),
        ("Gamma Ltd", "Mid-tier provider with standard offerings. Basic compliance. Email support only."),
        ("Delta Co", "Budget option with minimal features. New to the market. Limited support."),
    ]

    print("Evaluating 4 suppliers...")
    scores = []
    for name, proposal in sample_proposals:
        raw = evaluator.evaluate(proposal, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)

    print()

    # Calculate relative performance
    relative = calculate_relative_performance(scores)

    # Show leaderboard
    print(format_leaderboard(relative))
    print()

    # Show detailed view for top performer
    print("Detailed view for top performer:")
    print(format_relative_performance(relative[0]))
