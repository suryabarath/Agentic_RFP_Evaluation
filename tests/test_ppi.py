"""
Unit tests for the PPI (Proposal Performance Index) module.

Tests PPI calculation, grading, and component scores.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ppi import calculate_ppi, get_ppi_grade, PPIBreakdown
from src.scorer import SupplierScore, CriterionScore


def create_mock_score(
    total_weighted: float = 70.0,
    criteria_scores: list = None,
    risks: list = None
) -> SupplierScore:
    """Create a mock SupplierScore for testing."""
    if criteria_scores is None:
        # Default: 5 criteria with consistent 70% scores
        criteria_scores = [
            CriterionScore(
                criterion_id=i,
                name=f"Criterion {i}",
                raw_score=7,
                max_score=10,
                weight=20.0,
                weighted_score=14.0,
                percentage=70.0,
                justification="Test",
                evidence=[]
            )
            for i in range(1, 6)
        ]

    return SupplierScore(
        supplier_name="TestSupplier",
        total_weighted_score=total_weighted,
        total_raw_score=35,
        total_max_score=50,
        overall_percentage=70.0,
        criteria_scores=criteria_scores,
        risks=risks or [],
        overall_summary="Test summary",
        warnings_count=0
    )


class TestPPIGrading:
    """Tests for PPI grading."""

    def test_grade_a(self):
        """Score >= 90 should be A."""
        assert get_ppi_grade(90.0) == "A"
        assert get_ppi_grade(95.0) == "A"
        assert get_ppi_grade(100.0) == "A"

    def test_grade_b(self):
        """Score 80-89 should be B."""
        assert get_ppi_grade(80.0) == "B"
        assert get_ppi_grade(85.0) == "B"
        assert get_ppi_grade(89.9) == "B"

    def test_grade_c(self):
        """Score 70-79 should be C."""
        assert get_ppi_grade(70.0) == "C"
        assert get_ppi_grade(75.0) == "C"
        assert get_ppi_grade(79.9) == "C"

    def test_grade_d(self):
        """Score 60-69 should be D."""
        assert get_ppi_grade(60.0) == "D"
        assert get_ppi_grade(65.0) == "D"
        assert get_ppi_grade(69.9) == "D"

    def test_grade_f(self):
        """Score < 60 should be F."""
        assert get_ppi_grade(59.9) == "F"
        assert get_ppi_grade(55.0) == "F"
        assert get_ppi_grade(0.0) == "F"


class TestPPICalculation:
    """Tests for PPI calculation."""

    def test_basic_ppi_calculation(self):
        """Basic PPI calculation should work."""
        score = create_mock_score(total_weighted=70.0)
        ppi = calculate_ppi(score)

        assert isinstance(ppi, PPIBreakdown)
        assert ppi.supplier_name == "TestSupplier"
        assert ppi.ppi_score >= 0
        assert ppi.ppi_score <= 100

    def test_ppi_components_present(self):
        """PPI should have all component scores."""
        score = create_mock_score()
        ppi = calculate_ppi(score)

        assert hasattr(ppi, 'weighted_score')
        assert hasattr(ppi, 'consistency_score')
        assert hasattr(ppi, 'quality_score')
        assert hasattr(ppi, 'risk_penalty')

    def test_perfect_score_high_ppi(self):
        """Perfect scores should result in high PPI."""
        criteria = [
            CriterionScore(
                criterion_id=i,
                name=f"Criterion {i}",
                raw_score=10,
                max_score=10,
                weight=20.0,
                weighted_score=20.0,
                percentage=100.0,
                justification="Perfect",
                evidence=[]
            )
            for i in range(1, 6)
        ]
        score = create_mock_score(total_weighted=100.0, criteria_scores=criteria)
        ppi = calculate_ppi(score)

        assert ppi.ppi_score >= 90.0  # High PPI for perfect scores

    def test_risk_penalty_applied(self):
        """Risks should reduce PPI score."""
        no_risks = create_mock_score(risks=[])
        with_risks = create_mock_score(risks=["Risk 1", "Risk 2", "Risk 3"])

        ppi_no_risks = calculate_ppi(no_risks)
        ppi_with_risks = calculate_ppi(with_risks)

        assert ppi_with_risks.risk_penalty > 0
        assert ppi_with_risks.ppi_score < ppi_no_risks.ppi_score

    def test_ppi_grade_assigned(self):
        """PPI should have a grade."""
        score = create_mock_score(total_weighted=70.0)
        ppi = calculate_ppi(score)

        assert ppi.ppi_grade in ["A+", "A", "B", "C", "D", "F"]


class TestConsistencyScore:
    """Tests for consistency score component."""

    def test_consistent_scores_high_consistency(self):
        """Consistent criteria scores should give high consistency."""
        # All criteria at 70%
        criteria = [
            CriterionScore(
                criterion_id=i,
                name=f"Criterion {i}",
                raw_score=7,
                max_score=10,
                weight=20.0,
                weighted_score=14.0,
                percentage=70.0,
                justification="Test",
                evidence=[]
            )
            for i in range(1, 6)
        ]
        score = create_mock_score(criteria_scores=criteria)
        ppi = calculate_ppi(score)

        assert ppi.consistency_score >= 90.0  # High consistency

    def test_inconsistent_scores_low_consistency(self):
        """Inconsistent criteria scores should give lower consistency."""
        # Wide variation: 10%, 30%, 50%, 70%, 90%
        percentages = [10.0, 30.0, 50.0, 70.0, 90.0]
        criteria = [
            CriterionScore(
                criterion_id=i + 1,
                name=f"Criterion {i + 1}",
                raw_score=int(p / 10),
                max_score=10,
                weight=20.0,
                weighted_score=p / 5,
                percentage=p,
                justification="Test",
                evidence=[]
            )
            for i, p in enumerate(percentages)
        ]
        score = create_mock_score(criteria_scores=criteria)
        ppi = calculate_ppi(score)

        assert ppi.consistency_score < 80.0  # Lower consistency


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_criteria(self):
        """Empty criteria should still calculate PPI."""
        score = SupplierScore(
            supplier_name="Empty",
            total_weighted_score=0.0,
            total_raw_score=0,
            total_max_score=0,
            overall_percentage=0.0,
            criteria_scores=[],
            risks=[],
            overall_summary="",
            warnings_count=0
        )
        ppi = calculate_ppi(score)

        assert ppi.ppi_score >= 0
        assert ppi.ppi_grade == "F"

    def test_many_risks(self):
        """Many risks should significantly reduce PPI."""
        many_risks = [f"Risk {i}" for i in range(10)]
        score = create_mock_score(total_weighted=80.0, risks=many_risks)
        ppi = calculate_ppi(score)

        assert ppi.risk_count == 10
        assert ppi.risk_penalty > 0
