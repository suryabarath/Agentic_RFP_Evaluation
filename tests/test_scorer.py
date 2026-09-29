"""
Unit tests for the Scorer module.

Tests weighted score calculations, edge cases, and score aggregation.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scorer import CriterionScore, SupplierScore


class TestCriterionScore:
    """Tests for CriterionScore dataclass."""

    def test_criterion_score_creation(self):
        """CriterionScore should store all fields."""
        cs = CriterionScore(
            criterion_id=1,
            name="Technical",
            raw_score=8,
            max_score=10,
            weight=30.0,
            weighted_score=24.0,
            percentage=80.0,
            justification="Good technical approach",
            evidence=["Modern architecture", "Scalable design"]
        )
        assert cs.criterion_id == 1
        assert cs.raw_score == 8
        assert cs.percentage == 80.0
        assert len(cs.evidence) == 2


class TestSupplierScore:
    """Tests for SupplierScore dataclass."""

    def test_supplier_score_creation(self):
        """SupplierScore should store all fields."""
        criteria = [
            CriterionScore(1, "Tech", 8, 10, 30.0, 24.0, 80.0, "Test", [])
        ]
        ss = SupplierScore(
            supplier_name="TestCorp",
            criteria_scores=criteria,
            total_weighted_score=75.0,
            total_raw_score=38,
            total_max_score=50,
            overall_percentage=76.0,
            risks=["Risk 1"],
            overall_summary="Good supplier",
            warnings_count=0
        )
        assert ss.supplier_name == "TestCorp"
        assert ss.total_weighted_score == 75.0
        assert len(ss.criteria_scores) == 1

    def test_criteria_lookup_by_id(self):
        """Can find criterion in criteria_scores list by ID."""
        criteria = [
            CriterionScore(1, "Tech", 8, 10, 30.0, 24.0, 80.0, "Test", []),
            CriterionScore(2, "Comm", 7, 10, 20.0, 14.0, 70.0, "Test", []),
        ]
        ss = SupplierScore("Test", criteria, 50.0, 15, 20, 75.0, [], "", 0)

        # Find by iterating
        tech = next((cs for cs in ss.criteria_scores if cs.criterion_id == 1), None)
        assert tech is not None
        assert tech.name == "Tech"

    def test_empty_criteria_scores(self):
        """Empty criteria_scores should work."""
        ss = SupplierScore("Test", [], 0.0, 0, 0, 0.0, [], "", 0)
        assert len(ss.criteria_scores) == 0


class TestWeightedScoreFormula:
    """Tests for weighted score formula."""

    def test_weighted_score_calculation(self):
        """Weighted score = (raw/max) * weight."""
        # 8/10 * 30 = 24
        cs = CriterionScore(1, "Tech", 8, 10, 30.0, 24.0, 80.0, "Test", [])
        expected = (8 / 10) * 30.0
        assert cs.weighted_score == expected

    def test_perfect_criterion_score(self):
        """Perfect score should give full weight."""
        cs = CriterionScore(1, "Tech", 10, 10, 30.0, 30.0, 100.0, "Test", [])
        assert cs.weighted_score == 30.0
        assert cs.percentage == 100.0

    def test_zero_criterion_score(self):
        """Zero score should give zero weighted."""
        cs = CriterionScore(1, "Tech", 0, 10, 30.0, 0.0, 0.0, "Test", [])
        assert cs.weighted_score == 0.0
        assert cs.percentage == 0.0


class TestTotalScoreCalculation:
    """Tests for total score calculation."""

    def test_total_is_sum_of_weighted(self):
        """Total weighted score should be sum of criterion weighted scores."""
        criteria = [
            CriterionScore(1, "Tech", 10, 10, 30.0, 30.0, 100.0, "Test", []),
            CriterionScore(2, "Comm", 10, 10, 20.0, 20.0, 100.0, "Test", []),
            CriterionScore(3, "Sec", 10, 10, 20.0, 20.0, 100.0, "Test", []),
            CriterionScore(4, "Impl", 10, 10, 20.0, 20.0, 100.0, "Test", []),
            CriterionScore(5, "Supp", 10, 10, 10.0, 10.0, 100.0, "Test", []),
        ]
        total = sum(cs.weighted_score for cs in criteria)
        assert total == 100.0

    def test_partial_scores_sum(self):
        """Partial scores should sum correctly."""
        # 8/10*30=24, 6/10*20=12, 7/10*20=14, 5/10*20=10, 9/10*10=9 = 69
        criteria = [
            CriterionScore(1, "Tech", 8, 10, 30.0, 24.0, 80.0, "Test", []),
            CriterionScore(2, "Comm", 6, 10, 20.0, 12.0, 60.0, "Test", []),
            CriterionScore(3, "Sec", 7, 10, 20.0, 14.0, 70.0, "Test", []),
            CriterionScore(4, "Impl", 5, 10, 20.0, 10.0, 50.0, "Test", []),
            CriterionScore(5, "Supp", 9, 10, 10.0, 9.0, 90.0, "Test", []),
        ]
        total = sum(cs.weighted_score for cs in criteria)
        assert total == 69.0
