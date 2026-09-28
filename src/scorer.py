"""
Scoring Module

Calculates absolute weighted scores from validated LLM evaluations.
All calculations are deterministic Python - no LLM involvement.

Key Formula:
    Weighted Score = (raw_score / max_score) * weight
    Total Score = Sum of all weighted scores (out of 100)
"""

from typing import Dict, Any, List
from dataclasses import dataclass

from src.schemas import ValidatedEvaluation


@dataclass
class CriterionScore:
    """Score breakdown for a single criterion."""
    criterion_id: int
    name: str
    raw_score: int
    max_score: int
    weight: float  # Percentage (e.g., 30 for 30%)
    weighted_score: float  # Calculated: (raw/max) * weight
    percentage: float  # raw/max as percentage (0-100)
    justification: str
    evidence: str


@dataclass
class SupplierScore:
    """Complete score calculation for a supplier."""
    supplier_name: str
    criteria_scores: List[CriterionScore]
    total_weighted_score: float  # Sum of all weighted_scores (out of 100)
    total_raw_score: int  # Sum of raw scores
    total_max_score: int  # Sum of max scores
    overall_percentage: float  # total_raw / total_max * 100
    risks: List[str]
    overall_summary: str
    warnings_count: int


def calculate_supplier_score(
    validated_eval: ValidatedEvaluation,
    criteria_lookup: Dict[int, Dict[str, Any]]
) -> SupplierScore:
    """
    Calculate weighted scores for a supplier from their validated evaluation.

    Args:
        validated_eval: The validated evaluation from the LLM
        criteria_lookup: Dict mapping criterion_id to criterion details
                        (from database, includes name and weight)

    Returns:
        SupplierScore: Complete score breakdown

    Example:
        from src.database import get_active_criteria
        from src.validator import validate_llm_response
        from src.scorer import calculate_supplier_score

        criteria = get_active_criteria()
        criteria_lookup = {c['criterion_id']: c for c in criteria}

        validated, success = validate_llm_response(llm_result, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)

        print(f"{score.supplier_name}: {score.total_weighted_score:.2f}/100")
    """
    evaluation = validated_eval.evaluation
    criteria_scores = []
    total_weighted = 0.0
    total_raw = 0
    total_max = 0

    # Process each criterion result
    for criterion_result in evaluation.criteria:
        cid = criterion_result.criterion_id

        # Get criterion details from lookup
        criterion_info = criteria_lookup.get(cid)
        if criterion_info is None:
            # This shouldn't happen if validator worked correctly
            continue

        name = criterion_info['name']
        weight = criterion_info['weight']

        raw = criterion_result.score
        max_s = criterion_result.max_score

        # Calculate weighted score
        # Formula: (raw_score / max_score) * weight
        if max_s > 0:
            percentage = (raw / max_s) * 100
            weighted = (raw / max_s) * weight
        else:
            percentage = 0.0
            weighted = 0.0

        criterion_score = CriterionScore(
            criterion_id=cid,
            name=name,
            raw_score=raw,
            max_score=max_s,
            weight=weight,
            weighted_score=weighted,
            percentage=percentage,
            justification=criterion_result.justification,
            evidence=criterion_result.evidence
        )

        criteria_scores.append(criterion_score)
        total_weighted += weighted
        total_raw += raw
        total_max += max_s

    # Calculate overall percentage
    if total_max > 0:
        overall_percentage = (total_raw / total_max) * 100
    else:
        overall_percentage = 0.0

    # Sort criteria by criterion_id for consistency
    criteria_scores.sort(key=lambda x: x.criterion_id)

    return SupplierScore(
        supplier_name=evaluation.supplier_name,
        criteria_scores=criteria_scores,
        total_weighted_score=total_weighted,
        total_raw_score=total_raw,
        total_max_score=total_max,
        overall_percentage=overall_percentage,
        risks=evaluation.risks,
        overall_summary=evaluation.overall_summary,
        warnings_count=len(validated_eval.warnings)
    )


def format_score_summary(score: SupplierScore) -> str:
    """
    Format a score summary for display.

    Args:
        score: The calculated supplier score

    Returns:
        str: Formatted summary string
    """
    lines = []
    lines.append(f"═══ {score.supplier_name} ═══")
    lines.append(f"")
    lines.append(f"Total Weighted Score: {score.total_weighted_score:.2f} / 100")
    lines.append(f"Overall Percentage: {score.overall_percentage:.1f}%")
    lines.append(f"")
    lines.append("Criteria Breakdown:")

    for cs in score.criteria_scores:
        score_bar = "█" * int(cs.percentage / 10) + "░" * (10 - int(cs.percentage / 10))
        lines.append(
            f"  {cs.name}: {cs.raw_score}/{cs.max_score} "
            f"({cs.percentage:.0f}%) [Weight: {cs.weight}%] → {cs.weighted_score:.2f}"
        )

    lines.append("")
    lines.append(f"Warnings: {score.warnings_count}")

    if score.risks:
        lines.append(f"")
        lines.append(f"Risks ({len(score.risks)}):")
        for risk in score.risks:
            lines.append(f"  • {risk}")

    return "\n".join(lines)


def get_score_as_dict(score: SupplierScore) -> Dict[str, Any]:
    """
    Convert a SupplierScore to a dictionary for JSON/database storage.

    Args:
        score: The calculated supplier score

    Returns:
        dict: Score data as dictionary
    """
    return {
        "supplier_name": score.supplier_name,
        "total_weighted_score": round(score.total_weighted_score, 2),
        "total_raw_score": score.total_raw_score,
        "total_max_score": score.total_max_score,
        "overall_percentage": round(score.overall_percentage, 2),
        "warnings_count": score.warnings_count,
        "risks": score.risks,
        "overall_summary": score.overall_summary,
        "criteria": [
            {
                "criterion_id": cs.criterion_id,
                "name": cs.name,
                "raw_score": cs.raw_score,
                "max_score": cs.max_score,
                "weight": cs.weight,
                "weighted_score": round(cs.weighted_score, 2),
                "percentage": round(cs.percentage, 2),
                "justification": cs.justification,
                "evidence": cs.evidence
            }
            for cs in score.criteria_scores
        ]
    }


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response

    print("=== Testing Scorer ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}
    print(f"Loaded {len(criteria)} criteria")
    print()

    # Simulate getting a mock evaluation
    sample_text = """
    Our company offers a comprehensive solution with modern microservices architecture.
    We have 10 years of experience in similar implementations.
    Our pricing is competitive at $500,000 for the full implementation.
    We are ISO 27001 certified and SOC 2 compliant.
    We offer 24/7 support with guaranteed 4-hour response times.
    """

    print("Getting mock evaluation...")
    raw_result = evaluator.evaluate(sample_text, criteria, "Test Supplier Inc")

    print("Validating response...")
    validated, success = validate_llm_response(raw_result, criteria)
    print(f"Validation success: {success}, Warnings: {len(validated.warnings)}")
    print()

    print("Calculating scores...")
    score = calculate_supplier_score(validated, criteria_lookup)

    print()
    print(format_score_summary(score))
