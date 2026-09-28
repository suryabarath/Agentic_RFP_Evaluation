"""
Ranking Module

Implements deterministic ranking with clear tie-breaking rules.
Ensures the same inputs always produce the same ranking order.

Tie-Break Rules (in order):
1. Total Weighted Score (higher is better)
2. PPI Score (higher is better)
3. Fewer Risks (lower is better)
4. Fewer Validation Warnings (lower is better)
5. Higher score on highest-weight criterion
6. Alphabetical by supplier name (final deterministic fallback)

All calculations are deterministic Python - no LLM involvement.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.scorer import SupplierScore
from src.ppi import calculate_ppi, PPIBreakdown


class RankStatus(Enum):
    """Status indicating how ranking was determined."""
    CLEAR = "clear"              # Clear winner, no tie-break needed
    TIEBREAK_PPI = "tiebreak_ppi"  # Tie broken by PPI
    TIEBREAK_RISKS = "tiebreak_risks"  # Tie broken by risk count
    TIEBREAK_WARNINGS = "tiebreak_warnings"  # Tie broken by warnings
    TIEBREAK_CRITERION = "tiebreak_criterion"  # Tie broken by top criterion
    TIEBREAK_ALPHA = "tiebreak_alphabetical"  # Tie broken alphabetically


@dataclass
class RankedSupplier:
    """A supplier with their final rank and ranking details."""
    rank: int
    supplier_name: str

    # Scores
    weighted_score: float
    ppi_score: float

    # Tie-break factors
    risk_count: int
    warning_count: int
    top_criterion_score: float  # Score on highest-weight criterion

    # Ranking metadata
    rank_status: RankStatus
    tied_with: List[str] = field(default_factory=list)  # Names of suppliers with same weighted score

    # Full data references
    supplier_score: Optional[SupplierScore] = None
    ppi_breakdown: Optional[PPIBreakdown] = None


@dataclass
class RankingResult:
    """Complete ranking result for all suppliers."""
    rankings: List[RankedSupplier]
    total_suppliers: int
    ties_encountered: int
    tie_break_methods_used: List[str]

    def get_winner(self) -> Optional[RankedSupplier]:
        """Get the #1 ranked supplier."""
        return self.rankings[0] if self.rankings else None

    def get_top_n(self, n: int) -> List[RankedSupplier]:
        """Get top N ranked suppliers."""
        return self.rankings[:n]

    def get_by_name(self, name: str) -> Optional[RankedSupplier]:
        """Get ranking for a specific supplier."""
        for r in self.rankings:
            if r.supplier_name == name:
                return r
        return None


def _get_top_criterion_score(score: SupplierScore) -> float:
    """
    Get the score on the highest-weight criterion.
    Used as a tie-breaker.
    """
    if not score.criteria_scores:
        return 0.0

    # Find criterion with highest weight
    top_criterion = max(score.criteria_scores, key=lambda cs: cs.weight)
    return top_criterion.percentage


def _create_sort_key(
    score: SupplierScore,
    ppi: PPIBreakdown
) -> Tuple:
    """
    Create a sort key tuple for deterministic sorting.

    Returns tuple of (weighted_score, ppi, -risks, -warnings, top_criterion, name)
    Higher values sort first (except for name which is alphabetical).
    Risks and warnings are negated so lower values sort first.
    """
    top_criterion = _get_top_criterion_score(score)

    return (
        score.total_weighted_score,      # Primary: weighted score (higher first)
        ppi.ppi_score,                   # Secondary: PPI (higher first)
        -len(score.risks),               # Tertiary: fewer risks (negated)
        -score.warnings_count,           # Quaternary: fewer warnings (negated)
        top_criterion,                   # Quinary: top criterion score
        score.supplier_name.lower()      # Final: alphabetical (for determinism)
    )


def _determine_rank_status(
    current: Tuple,
    previous: Optional[Tuple]
) -> Tuple[RankStatus, int]:
    """
    Determine how the rank was determined relative to previous supplier.

    Returns (RankStatus, tie_break_level)
    tie_break_level: 0=clear, 1=ppi, 2=risks, 3=warnings, 4=criterion, 5=alpha
    """
    if previous is None:
        return RankStatus.CLEAR, 0

    # Compare each level
    if current[0] != previous[0]:  # Different weighted score
        return RankStatus.CLEAR, 0
    if current[1] != previous[1]:  # Different PPI
        return RankStatus.TIEBREAK_PPI, 1
    if current[2] != previous[2]:  # Different risk count
        return RankStatus.TIEBREAK_RISKS, 2
    if current[3] != previous[3]:  # Different warning count
        return RankStatus.TIEBREAK_WARNINGS, 3
    if current[4] != previous[4]:  # Different top criterion
        return RankStatus.TIEBREAK_CRITERION, 4

    # Must be alphabetical
    return RankStatus.TIEBREAK_ALPHA, 5


def rank_suppliers(scores: List[SupplierScore]) -> RankingResult:
    """
    Rank suppliers with deterministic tie-breaking.

    Args:
        scores: List of supplier scores

    Returns:
        RankingResult: Complete ranking with tie-break details

    Example:
        from src.ranking import rank_suppliers

        result = rank_suppliers(scores)
        winner = result.get_winner()
        print(f"Winner: {winner.supplier_name} with {winner.weighted_score:.2f}")
    """
    if not scores:
        return RankingResult(
            rankings=[],
            total_suppliers=0,
            ties_encountered=0,
            tie_break_methods_used=[]
        )

    # Calculate PPI for all suppliers
    ppis = {s.supplier_name: calculate_ppi(s) for s in scores}

    # Create sort keys and sort
    scored_items = []
    for score in scores:
        ppi = ppis[score.supplier_name]
        sort_key = _create_sort_key(score, ppi)
        scored_items.append((sort_key, score, ppi))

    # Sort by key (descending for scores, but tuple handles this)
    # We need to reverse because higher scores should come first
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Build rankings
    rankings = []
    ties_encountered = 0
    tie_break_methods = set()
    previous_key = None

    # Find all suppliers with same weighted score (for tied_with field)
    score_groups: Dict[float, List[str]] = {}
    for sort_key, score, ppi in scored_items:
        ws = score.total_weighted_score
        if ws not in score_groups:
            score_groups[ws] = []
        score_groups[ws].append(score.supplier_name)

    for rank, (sort_key, score, ppi) in enumerate(scored_items, 1):
        # Determine rank status
        rank_status, tie_level = _determine_rank_status(sort_key, previous_key)

        if tie_level > 0:
            ties_encountered += 1
            tie_break_methods.add(rank_status.value)

        # Find tied suppliers
        tied_with = [
            name for name in score_groups[score.total_weighted_score]
            if name != score.supplier_name
        ]

        ranked = RankedSupplier(
            rank=rank,
            supplier_name=score.supplier_name,
            weighted_score=round(score.total_weighted_score, 2),
            ppi_score=round(ppi.ppi_score, 2),
            risk_count=len(score.risks),
            warning_count=score.warnings_count,
            top_criterion_score=round(_get_top_criterion_score(score), 2),
            rank_status=rank_status,
            tied_with=tied_with,
            supplier_score=score,
            ppi_breakdown=ppi
        )
        rankings.append(ranked)
        previous_key = sort_key

    return RankingResult(
        rankings=rankings,
        total_suppliers=len(scores),
        ties_encountered=ties_encountered,
        tie_break_methods_used=list(tie_break_methods)
    )


def format_ranking_table(result: RankingResult) -> str:
    """
    Format ranking as a table.

    Args:
        result: The ranking result

    Returns:
        str: Formatted table
    """
    lines = []
    lines.append("═" * 80)
    lines.append("FINAL SUPPLIER RANKING")
    lines.append("═" * 80)
    lines.append("")

    if result.ties_encountered > 0:
        lines.append(f"Note: {result.ties_encountered} tie(s) resolved using: {', '.join(result.tie_break_methods_used)}")
        lines.append("")

    lines.append(f"{'Rank':<6} {'Supplier':<25} {'Score':<10} {'PPI':<10} {'Risks':<7} {'Status'}")
    lines.append("-" * 80)

    status_icons = {
        RankStatus.CLEAR: "",
        RankStatus.TIEBREAK_PPI: "(PPI)",
        RankStatus.TIEBREAK_RISKS: "(Risks)",
        RankStatus.TIEBREAK_WARNINGS: "(Warn)",
        RankStatus.TIEBREAK_CRITERION: "(Crit)",
        RankStatus.TIEBREAK_ALPHA: "(A-Z)",
    }

    for r in result.rankings:
        rank_display = f"#{r.rank}"
        if r.rank == 1:
            rank_display = "#1 🏆"

        status = status_icons.get(r.rank_status, "")
        tied_note = f" [tied w/ {len(r.tied_with)}]" if r.tied_with else ""

        lines.append(
            f"{rank_display:<6} {r.supplier_name:<25} "
            f"{r.weighted_score:<10.2f} {r.ppi_score:<10.2f} "
            f"{r.risk_count:<7} {status}{tied_note}"
        )

    lines.append("")
    lines.append("═" * 80)

    return "\n".join(lines)


def format_ranking_details(ranked: RankedSupplier) -> str:
    """
    Format detailed ranking info for a single supplier.

    Args:
        ranked: The ranked supplier

    Returns:
        str: Formatted details
    """
    lines = []
    lines.append(f"═══ Rank #{ranked.rank}: {ranked.supplier_name} ═══")
    lines.append("")
    lines.append(f"Weighted Score: {ranked.weighted_score:.2f}/100")
    lines.append(f"PPI Score: {ranked.ppi_score:.2f}/100")
    lines.append(f"Risks: {ranked.risk_count}")
    lines.append(f"Warnings: {ranked.warning_count}")
    lines.append(f"Top Criterion Score: {ranked.top_criterion_score:.1f}%")
    lines.append("")

    if ranked.rank_status != RankStatus.CLEAR:
        lines.append(f"Rank Determined By: {ranked.rank_status.value}")

    if ranked.tied_with:
        lines.append(f"Tied With: {', '.join(ranked.tied_with)}")

    return "\n".join(lines)


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score

    print("=== Testing Deterministic Ranking ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    # Create suppliers with intentional ties
    sample_proposals = [
        ("Alpha Corp", "Strong technical solution with modern architecture. Good security practices. Competitive pricing."),
        ("Beta Inc", "Strong technical solution with modern architecture. Good security practices. Competitive pricing."),  # Same as Alpha
        ("Gamma Ltd", "Premium enterprise solution. Excellent security. Higher pricing but comprehensive support."),
        ("Delta Co", "Budget-friendly option. Basic features. Limited support."),
        ("Alpha Corp", "Strong technical solution with modern architecture. Good security practices. Competitive pricing."),  # Duplicate name test
    ]

    print("Evaluating 5 suppliers (including intentional duplicates for tie testing)...")
    scores = []
    seen_names = set()

    for name, proposal in sample_proposals:
        # Make names unique if duplicated
        unique_name = name
        counter = 2
        while unique_name in seen_names:
            unique_name = f"{name} {counter}"
            counter += 1
        seen_names.add(unique_name)

        raw = evaluator.evaluate(proposal, criteria, unique_name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)
        print(f"  {unique_name}: {score.total_weighted_score:.2f}")

    print()

    # Rank suppliers
    result = rank_suppliers(scores)

    # Show ranking table
    print(format_ranking_table(result))
    print()

    # Show winner details
    winner = result.get_winner()
    if winner:
        print("WINNER DETAILS:")
        print(format_ranking_details(winner))
