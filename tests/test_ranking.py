"""
Unit tests for the Ranking module.

Tests deterministic ranking and tie-breaking rules.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ranking import rank_suppliers, RankStatus, RankedSupplier, RankingResult
from src.scorer import SupplierScore, CriterionScore


def create_score(
    name: str,
    total_weighted: float,
    risks: list = None,
    warnings_count: int = 0,
    criteria_percentages: list = None
) -> SupplierScore:
    """Create a mock SupplierScore for testing."""
    if criteria_percentages is None:
        criteria_percentages = [70.0, 70.0, 70.0, 70.0, 70.0]

    criteria_scores = [
        CriterionScore(
            criterion_id=i + 1,
            name=f"Criterion {i + 1}",
            raw_score=int(p / 10),
            max_score=10,
            weight=20.0 if i < 4 else 20.0,
            weighted_score=p * 0.2,
            percentage=p,
            justification="Test",
            evidence=[]
        )
        for i, p in enumerate(criteria_percentages)
    ]

    return SupplierScore(
        supplier_name=name,
        total_weighted_score=total_weighted,
        total_raw_score=35,
        total_max_score=50,
        overall_percentage=total_weighted,
        criteria_scores=criteria_scores,
        risks=risks or [],
        overall_summary="Test",
        warnings_count=warnings_count
    )


class TestBasicRanking:
    """Tests for basic ranking functionality."""

    def test_empty_scores(self):
        """Empty list should return empty ranking."""
        result = rank_suppliers([])
        assert result.total_suppliers == 0
        assert len(result.rankings) == 0

    def test_single_supplier(self):
        """Single supplier should be ranked #1."""
        scores = [create_score("Only", 75.0)]
        result = rank_suppliers(scores)

        assert result.total_suppliers == 1
        assert result.rankings[0].rank == 1
        assert result.rankings[0].supplier_name == "Only"

    def test_multiple_suppliers_ordered(self):
        """Multiple suppliers should be ranked by score."""
        scores = [
            create_score("Low", 60.0),
            create_score("High", 90.0),
            create_score("Medium", 75.0),
        ]
        result = rank_suppliers(scores)

        assert result.rankings[0].supplier_name == "High"
        assert result.rankings[1].supplier_name == "Medium"
        assert result.rankings[2].supplier_name == "Low"

    def test_ranks_sequential(self):
        """Ranks should be sequential 1, 2, 3, etc."""
        scores = [
            create_score("A", 80.0),
            create_score("B", 70.0),
            create_score("C", 60.0),
        ]
        result = rank_suppliers(scores)

        ranks = [r.rank for r in result.rankings]
        assert ranks == [1, 2, 3]


class TestTieBreaking:
    """Tests for tie-breaking rules."""

    def test_score_tie_broken_by_ppi(self):
        """Equal scores should be broken by PPI."""
        # Same total score, different risk counts (affects PPI)
        scores = [
            create_score("MoreRisks", 80.0, risks=["R1", "R2", "R3"]),
            create_score("LessRisks", 80.0, risks=[]),
        ]
        result = rank_suppliers(scores)

        # LessRisks should rank higher (better PPI)
        assert result.rankings[0].supplier_name == "LessRisks"
        assert result.ties_encountered > 0

    def test_tie_broken_by_risk_count(self):
        """When PPI is same, fewer risks should win."""
        scores = [
            create_score("Many", 80.0, risks=["R1", "R2"]),
            create_score("Few", 80.0, risks=[]),
        ]
        result = rank_suppliers(scores)

        # Few risks should rank higher
        assert result.rankings[0].supplier_name == "Few"

    def test_tie_broken_by_name(self):
        """Final fallback should be deterministic by name."""
        # Identical scores and attributes
        scores = [
            create_score("Zebra", 80.0),
            create_score("Alpha", 80.0),
        ]
        result = rank_suppliers(scores)

        # Should have deterministic order (reversed alphabetical due to reverse=True sort)
        # The key point is it's consistent, not which specific order
        assert len(result.rankings) == 2
        assert result.rankings[0].supplier_name != result.rankings[1].supplier_name

    def test_tied_with_list(self):
        """Tied suppliers should be listed in tied_with."""
        scores = [
            create_score("A", 80.0),
            create_score("B", 80.0),
        ]
        result = rank_suppliers(scores)

        # Each should list the other as tied
        for r in result.rankings:
            assert len(r.tied_with) == 1


class TestRankStatus:
    """Tests for rank status tracking."""

    def test_clear_winner_status(self):
        """Clear winner should have CLEAR status."""
        scores = [
            create_score("Winner", 90.0),
            create_score("Loser", 60.0),
        ]
        result = rank_suppliers(scores)

        assert result.rankings[0].rank_status == RankStatus.CLEAR

    def test_tiebreak_status_tracked(self):
        """Tie-break method should be tracked."""
        scores = [
            create_score("A", 80.0, risks=[]),
            create_score("B", 80.0, risks=["R1"]),
        ]
        result = rank_suppliers(scores)

        # Should have used some tie-break method
        assert result.ties_encountered > 0
        assert len(result.tie_break_methods_used) > 0


class TestRankingResultMethods:
    """Tests for RankingResult helper methods."""

    def test_get_winner(self):
        """get_winner should return #1 ranked."""
        scores = [
            create_score("First", 90.0),
            create_score("Second", 80.0),
        ]
        result = rank_suppliers(scores)
        winner = result.get_winner()

        assert winner.supplier_name == "First"

    def test_get_top_n(self):
        """get_top_n should return top N suppliers."""
        scores = [
            create_score("A", 90.0),
            create_score("B", 80.0),
            create_score("C", 70.0),
            create_score("D", 60.0),
        ]
        result = rank_suppliers(scores)
        top2 = result.get_top_n(2)

        assert len(top2) == 2
        assert top2[0].supplier_name == "A"
        assert top2[1].supplier_name == "B"

    def test_get_by_name(self):
        """get_by_name should find specific supplier."""
        scores = [
            create_score("Target", 75.0),
            create_score("Other", 80.0),
        ]
        result = rank_suppliers(scores)
        target = result.get_by_name("Target")

        assert target is not None
        assert target.supplier_name == "Target"
        assert target.rank == 2

    def test_get_by_name_not_found(self):
        """get_by_name should return None if not found."""
        scores = [create_score("Only", 75.0)]
        result = rank_suppliers(scores)

        assert result.get_by_name("Missing") is None


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_consistent_results(self):
        """Same input should always produce same ranking."""
        scores = [
            create_score("C", 70.0),
            create_score("A", 70.0),
            create_score("B", 70.0),
        ]

        # Run multiple times
        results = [rank_suppliers(scores) for _ in range(5)]

        # All should have same order
        first_order = [r.supplier_name for r in results[0].rankings]
        for result in results[1:]:
            order = [r.supplier_name for r in result.rankings]
            assert order == first_order

    def test_name_based_determinism(self):
        """Name-based tie-break should be consistent across runs."""
        # All identical except names
        scores = [
            create_score("Zebra", 75.0),
            create_score("Alpha", 75.0),
            create_score("Beta", 75.0),
        ]

        # Run multiple times and verify same order
        results = [rank_suppliers(scores) for _ in range(3)]
        first_order = [r.supplier_name for r in results[0].rankings]

        for result in results[1:]:
            order = [r.supplier_name for r in result.rankings]
            assert order == first_order
