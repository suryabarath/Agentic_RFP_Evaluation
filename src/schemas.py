"""
Pydantic Schemas for LLM Response Validation

These models define the expected structure of LLM evaluation responses.
Using Pydantic ensures we catch malformed responses before processing.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class CriterionResult(BaseModel):
    """
    Evaluation result for a single criterion.

    Example:
    {
        "criterion_id": 1,
        "score": 8,
        "max_score": 10,
        "justification": "Strong technical architecture with microservices...",
        "evidence": "Page 5: 'Our solution uses Kubernetes for orchestration...'"
    }
    """

    criterion_id: int = Field(
        ...,
        description="The ID of the criterion being evaluated",
        ge=1  # Must be >= 1
    )

    score: int = Field(
        ...,
        description="The score assigned for this criterion",
        ge=0  # Must be >= 0
    )

    max_score: int = Field(
        ...,
        description="Maximum possible score for this criterion",
        ge=1  # Must be >= 1
    )

    justification: str = Field(
        ...,
        description="Explanation of why this score was assigned",
        min_length=10  # Must have at least 10 characters
    )

    evidence: str = Field(
        ...,
        description="Specific evidence from the proposal supporting this score",
        min_length=10  # Must have at least 10 characters
    )

    @field_validator('score')
    @classmethod
    def score_must_not_exceed_max(cls, v, info):
        """Validate that score does not exceed max_score."""
        # Note: This validator runs before max_score is available
        # We'll do the cross-field validation in the parent model
        return v


class SupplierEvaluation(BaseModel):
    """
    Complete evaluation result for a supplier.

    This is the expected structure of the LLM's JSON response.

    Example:
    {
        "supplier_name": "Apex Systems",
        "criteria": [
            {"criterion_id": 1, "score": 8, "max_score": 10, ...},
            {"criterion_id": 2, "score": 7, "max_score": 10, ...}
        ],
        "risks": [
            "Timeline appears aggressive for the scope",
            "Limited experience with similar scale projects"
        ],
        "overall_summary": "Strong technical proposal with competitive pricing..."
    }
    """

    supplier_name: str = Field(
        ...,
        description="Name of the supplier being evaluated",
        min_length=1
    )

    criteria: List[CriterionResult] = Field(
        ...,
        description="List of criterion evaluation results",
        min_length=1  # Must have at least one criterion
    )

    risks: List[str] = Field(
        default_factory=list,
        description="List of identified risks in the proposal"
    )

    overall_summary: str = Field(
        ...,
        description="Overall summary of the evaluation",
        min_length=20  # Must have at least 20 characters
    )

    @field_validator('criteria')
    @classmethod
    def validate_criteria_scores(cls, criteria_list):
        """Validate that no score exceeds its max_score."""
        for criterion in criteria_list:
            if criterion.score > criterion.max_score:
                raise ValueError(
                    f"Criterion {criterion.criterion_id}: "
                    f"score ({criterion.score}) exceeds max_score ({criterion.max_score})"
                )
        return criteria_list

    def get_criterion_by_id(self, criterion_id: int) -> Optional[CriterionResult]:
        """Get a criterion result by its ID."""
        for criterion in self.criteria:
            if criterion.criterion_id == criterion_id:
                return criterion
        return None

    def get_all_criterion_ids(self) -> List[int]:
        """Get list of all criterion IDs in the evaluation."""
        return [c.criterion_id for c in self.criteria]


class ValidationWarning(BaseModel):
    """
    A warning generated during validation.

    Warnings don't stop processing but should be logged/displayed.
    """

    warning_type: str = Field(
        ...,
        description="Type of warning (e.g., 'missing_criterion', 'score_adjusted')"
    )

    message: str = Field(
        ...,
        description="Human-readable warning message"
    )

    criterion_id: Optional[int] = Field(
        default=None,
        description="Related criterion ID, if applicable"
    )


class ValidatedEvaluation(BaseModel):
    """
    Evaluation result after validation and normalization.

    Contains the original evaluation plus any warnings generated.
    """

    evaluation: SupplierEvaluation = Field(
        ...,
        description="The validated evaluation data"
    )

    warnings: List[ValidationWarning] = Field(
        default_factory=list,
        description="List of validation warnings"
    )

    is_valid: bool = Field(
        default=True,
        description="Whether the evaluation passed validation"
    )

    def add_warning(self, warning_type: str, message: str, criterion_id: int = None):
        """Add a validation warning."""
        self.warnings.append(ValidationWarning(
            warning_type=warning_type,
            message=message,
            criterion_id=criterion_id
        ))

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


# Example usage and testing
if __name__ == "__main__":
    # Test valid data
    print("Testing valid evaluation data...")

    valid_data = {
        "supplier_name": "Apex Systems",
        "criteria": [
            {
                "criterion_id": 1,
                "score": 8,
                "max_score": 10,
                "justification": "Strong technical architecture with microservices design",
                "evidence": "Page 5 states: 'Our solution uses Kubernetes for orchestration'"
            },
            {
                "criterion_id": 2,
                "score": 7,
                "max_score": 10,
                "justification": "Implementation plan is detailed but timeline is aggressive",
                "evidence": "Page 8 shows a 6-month implementation timeline with clear milestones"
            }
        ],
        "risks": [
            "Timeline appears aggressive for the scope",
            "Limited experience with similar scale projects"
        ],
        "overall_summary": "Strong technical proposal with competitive pricing. The team has relevant experience but the timeline may need adjustment."
    }

    try:
        evaluation = SupplierEvaluation(**valid_data)
        print(f"✓ Valid! Supplier: {evaluation.supplier_name}")
        print(f"  Criteria count: {len(evaluation.criteria)}")
        print(f"  Risks count: {len(evaluation.risks)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")

    # Test invalid data (score exceeds max)
    print("\nTesting invalid data (score > max_score)...")

    invalid_data = {
        "supplier_name": "Test Company",
        "criteria": [
            {
                "criterion_id": 1,
                "score": 15,  # Invalid: exceeds max_score of 10
                "max_score": 10,
                "justification": "This score is too high",
                "evidence": "Some evidence here"
            }
        ],
        "risks": [],
        "overall_summary": "This should fail validation because score exceeds max."
    }

    try:
        evaluation = SupplierEvaluation(**invalid_data)
        print(f"✗ Should have failed but didn't!")
    except Exception as e:
        print(f"✓ Correctly rejected: {type(e).__name__}")

    print("\nSchema validation tests complete!")
