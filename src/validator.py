"""
LLM Response Validator

Validates and normalizes LLM evaluation responses.
Handles edge cases and records warnings for any issues.
"""

from typing import Dict, Any, List, Tuple
from pydantic import ValidationError

from src.schemas import SupplierEvaluation, CriterionResult, ValidatedEvaluation


def validate_llm_response(
    raw_response: Dict[str, Any],
    expected_criteria: List[Dict[str, Any]]
) -> Tuple[ValidatedEvaluation, bool]:
    """
    Validate and normalize an LLM evaluation response.

    Args:
        raw_response: The raw dictionary from the LLM
        expected_criteria: List of criteria from database (to check completeness)

    Returns:
        Tuple of (ValidatedEvaluation, success: bool)

    Example:
        validated, success = validate_llm_response(llm_result, criteria)
        if success:
            print(f"Valid! Warnings: {len(validated.warnings)}")
        else:
            print("Validation failed")
    """
    warnings = []
    normalized_response = raw_response.copy()

    # Step 1: Ensure required fields exist
    if 'supplier_name' not in normalized_response:
        normalized_response['supplier_name'] = 'Unknown Supplier'
        warnings.append({
            'type': 'missing_field',
            'message': 'supplier_name was missing, set to "Unknown Supplier"'
        })

    if 'criteria' not in normalized_response:
        normalized_response['criteria'] = []
        warnings.append({
            'type': 'missing_field',
            'message': 'criteria list was missing'
        })

    if 'risks' not in normalized_response:
        normalized_response['risks'] = []
        warnings.append({
            'type': 'missing_field',
            'message': 'risks list was missing, set to empty'
        })

    if 'overall_summary' not in normalized_response:
        normalized_response['overall_summary'] = 'No summary provided by evaluator.'
        warnings.append({
            'type': 'missing_field',
            'message': 'overall_summary was missing'
        })

    # Step 2: Normalize criteria
    normalized_criteria, criteria_warnings = _normalize_criteria(
        normalized_response.get('criteria', []),
        expected_criteria
    )
    normalized_response['criteria'] = normalized_criteria
    warnings.extend(criteria_warnings)

    # Step 3: Validate with Pydantic
    try:
        evaluation = SupplierEvaluation(**normalized_response)

        # Create validated evaluation with warnings
        validated = ValidatedEvaluation(
            evaluation=evaluation,
            warnings=[],
            is_valid=True
        )

        # Add warnings
        for w in warnings:
            validated.add_warning(
                warning_type=w['type'],
                message=w['message'],
                criterion_id=w.get('criterion_id')
            )

        return validated, True

    except ValidationError as e:
        # Pydantic validation failed
        error_messages = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            error_messages.append(f"{field}: {msg}")

        # Create a failed validation result
        # We'll create a minimal valid structure to allow partial processing
        fallback_criteria = _create_fallback_criteria(expected_criteria)

        fallback_evaluation = SupplierEvaluation(
            supplier_name=normalized_response.get('supplier_name', 'Unknown'),
            criteria=fallback_criteria,
            risks=[],
            overall_summary="Evaluation failed validation. Using fallback scores."
        )

        validated = ValidatedEvaluation(
            evaluation=fallback_evaluation,
            warnings=[],
            is_valid=False
        )

        validated.add_warning(
            warning_type='validation_error',
            message=f"Pydantic validation failed: {'; '.join(error_messages)}"
        )

        for w in warnings:
            validated.add_warning(
                warning_type=w['type'],
                message=w['message'],
                criterion_id=w.get('criterion_id')
            )

        return validated, False


def _normalize_criteria(
    raw_criteria: List[Dict[str, Any]],
    expected_criteria: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Normalize the criteria list.

    - Ensures all expected criteria are present
    - Fixes scores outside valid range
    - Handles duplicates
    - Fixes missing fields

    Returns:
        Tuple of (normalized_criteria, warnings)
    """
    warnings = []
    normalized = []

    # Create lookup of expected criteria
    expected_map = {c['criterion_id']: c for c in expected_criteria}
    found_ids = set()

    # Process each criterion from LLM response
    for raw_criterion in raw_criteria:
        criterion_id = raw_criterion.get('criterion_id')

        # Skip if no ID
        if criterion_id is None:
            warnings.append({
                'type': 'invalid_criterion',
                'message': 'Criterion without ID was skipped'
            })
            continue

        # Check for duplicate
        if criterion_id in found_ids:
            warnings.append({
                'type': 'duplicate_criterion',
                'message': f'Duplicate criterion ID {criterion_id} was skipped',
                'criterion_id': criterion_id
            })
            continue

        found_ids.add(criterion_id)

        # Get expected max_score
        expected = expected_map.get(criterion_id)
        if expected is None:
            warnings.append({
                'type': 'unknown_criterion',
                'message': f'Criterion ID {criterion_id} not in expected list, skipped',
                'criterion_id': criterion_id
            })
            continue

        max_score = expected['max_score']

        # Normalize the criterion
        normalized_criterion, criterion_warnings = _normalize_single_criterion(
            raw_criterion, max_score, criterion_id
        )
        normalized.append(normalized_criterion)
        warnings.extend(criterion_warnings)

    # Add missing criteria with score = 0
    for expected_id, expected_criterion in expected_map.items():
        if expected_id not in found_ids:
            warnings.append({
                'type': 'missing_criterion',
                'message': f'Criterion "{expected_criterion["name"]}" (ID: {expected_id}) was missing, added with score 0',
                'criterion_id': expected_id
            })
            normalized.append({
                'criterion_id': expected_id,
                'score': 0,
                'max_score': expected_criterion['max_score'],
                'justification': 'Not evaluated by LLM - criterion was missing from response',
                'evidence': 'No evidence available'
            })

    # Sort by criterion_id for consistency
    normalized.sort(key=lambda x: x['criterion_id'])

    return normalized, warnings


def _normalize_single_criterion(
    raw: Dict[str, Any],
    max_score: int,
    criterion_id: int
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Normalize a single criterion entry.

    Returns:
        Tuple of (normalized_criterion, warnings)
    """
    warnings = []
    normalized = {}

    # ID
    normalized['criterion_id'] = criterion_id

    # Max score (use expected value)
    normalized['max_score'] = max_score

    # Score - normalize to valid range
    raw_score = raw.get('score', 0)

    # Try to convert to int if needed
    try:
        score = int(raw_score)
    except (ValueError, TypeError):
        score = 0
        warnings.append({
            'type': 'invalid_score',
            'message': f'Criterion {criterion_id}: score "{raw_score}" could not be converted to int, set to 0',
            'criterion_id': criterion_id
        })

    # Clamp to valid range
    if score < 0:
        warnings.append({
            'type': 'score_adjusted',
            'message': f'Criterion {criterion_id}: score {score} was below 0, set to 0',
            'criterion_id': criterion_id
        })
        score = 0
    elif score > max_score:
        warnings.append({
            'type': 'score_adjusted',
            'message': f'Criterion {criterion_id}: score {score} exceeded max {max_score}, clamped to {max_score}',
            'criterion_id': criterion_id
        })
        score = max_score

    normalized['score'] = score

    # Justification
    justification = raw.get('justification', '')
    if not justification or len(str(justification)) < 10:
        justification = 'No detailed justification provided'
        warnings.append({
            'type': 'missing_justification',
            'message': f'Criterion {criterion_id}: justification was missing or too short',
            'criterion_id': criterion_id
        })
    normalized['justification'] = str(justification)

    # Evidence
    evidence = raw.get('evidence', '')
    if not evidence or len(str(evidence)) < 10:
        evidence = 'No specific evidence cited'
        warnings.append({
            'type': 'missing_evidence',
            'message': f'Criterion {criterion_id}: evidence was missing or too short',
            'criterion_id': criterion_id
        })
    normalized['evidence'] = str(evidence)

    return normalized, warnings


def _create_fallback_criteria(
    expected_criteria: List[Dict[str, Any]]
) -> List[CriterionResult]:
    """
    Create fallback criteria with zero scores when validation completely fails.
    """
    fallback = []
    for criterion in expected_criteria:
        fallback.append(CriterionResult(
            criterion_id=criterion['criterion_id'],
            score=0,
            max_score=criterion['max_score'],
            justification='Validation failed - using fallback score of 0',
            evidence='No evidence available due to validation failure'
        ))
    return fallback


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria

    print("=== Testing Validator ===")
    print()

    # Get expected criteria
    criteria = get_active_criteria()
    print(f"Loaded {len(criteria)} expected criteria")
    print()

    # Test 1: Valid response
    print("Test 1: Valid response")
    valid_response = {
        "supplier_name": "Test Corp",
        "criteria": [
            {"criterion_id": 1, "score": 8, "max_score": 10, "justification": "Good technical approach", "evidence": "Page 5 shows architecture"},
            {"criterion_id": 2, "score": 7, "max_score": 10, "justification": "Solid implementation plan", "evidence": "Timeline on page 8"},
            {"criterion_id": 3, "score": 6, "max_score": 10, "justification": "Fair pricing", "evidence": "Cost breakdown provided"},
            {"criterion_id": 4, "score": 9, "max_score": 10, "justification": "Strong security", "evidence": "SOC 2 certified"},
            {"criterion_id": 5, "score": 7, "max_score": 10, "justification": "Good support model", "evidence": "24/7 support offered"},
        ],
        "risks": ["Timeline is aggressive"],
        "overall_summary": "Solid proposal with good technical approach and reasonable pricing."
    }

    validated, success = validate_llm_response(valid_response, criteria)
    print(f"  Success: {success}")
    print(f"  Warnings: {len(validated.warnings)}")
    print()

    # Test 2: Response with issues
    print("Test 2: Response with issues (missing criterion, score > max)")
    problematic_response = {
        "supplier_name": "Problem Corp",
        "criteria": [
            {"criterion_id": 1, "score": 15, "max_score": 10, "justification": "Too high!", "evidence": "Some evidence"},
            {"criterion_id": 2, "score": -5, "max_score": 10, "justification": "Negative!", "evidence": "Some evidence"},
            {"criterion_id": 3, "score": 7, "max_score": 10, "justification": "OK", "evidence": "OK"},
            # Missing criterion 4 and 5
        ],
        "overall_summary": "Test summary for validation"
    }

    validated, success = validate_llm_response(problematic_response, criteria)
    print(f"  Success: {success}")
    print(f"  Warnings: {len(validated.warnings)}")
    for w in validated.warnings:
        print(f"    - [{w.warning_type}] {w.message}")
    print()

    print("Validator tests complete!")
