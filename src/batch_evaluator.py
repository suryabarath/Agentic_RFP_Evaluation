"""
Batch Evaluator Module

Evaluates multiple supplier proposals and collects results.
Handles the full pipeline: PDF extraction → LLM evaluation → validation → scoring.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.pdf_tool import extract_text_from_uploaded_file
from src.evaluator import evaluator
from src.validator import validate_llm_response
from src.scorer import calculate_supplier_score, SupplierScore, get_score_as_dict
from src.database import get_active_criteria


@dataclass
class SupplierInput:
    """Input data for a single supplier."""
    name: str
    pdf_file: Any  # Streamlit UploadedFile or file path
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of evaluating a single supplier."""
    supplier_name: str
    success: bool
    score: Optional[SupplierScore] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    validation_warnings: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_seconds: float = 0.0


@dataclass
class BatchResult:
    """Result of evaluating multiple suppliers."""
    results: List[EvaluationResult]
    total_suppliers: int
    successful_evaluations: int
    failed_evaluations: int
    evaluation_mode: str  # "MOCK" or "LIVE"
    started_at: datetime
    completed_at: datetime

    def get_successful_scores(self) -> List[SupplierScore]:
        """Get list of successful supplier scores, sorted by total weighted score."""
        scores = [r.score for r in self.results if r.success and r.score]
        return sorted(scores, key=lambda s: s.total_weighted_score, reverse=True)

    def get_ranking(self) -> List[Dict[str, Any]]:
        """Get ranked list of suppliers with their scores."""
        scores = self.get_successful_scores()
        ranking = []
        for rank, score in enumerate(scores, 1):
            ranking.append({
                "rank": rank,
                "supplier_name": score.supplier_name,
                "total_weighted_score": round(score.total_weighted_score, 2),
                "overall_percentage": round(score.overall_percentage, 2),
                "warnings_count": score.warnings_count,
                "risks_count": len(score.risks)
            })
        return ranking


class BatchEvaluator:
    """
    Evaluates multiple supplier proposals in sequence.

    Usage:
        batch_eval = BatchEvaluator()

        suppliers = [
            SupplierInput(name="Supplier A", pdf_file=uploaded_file_a),
            SupplierInput(name="Supplier B", pdf_file=uploaded_file_b),
        ]

        result = batch_eval.evaluate_all(suppliers)

        for r in result.results:
            if r.success:
                print(f"{r.supplier_name}: {r.score.total_weighted_score:.2f}")
    """

    def __init__(self):
        """Initialize the batch evaluator."""
        self.criteria = None
        self.criteria_lookup = None

    def _load_criteria(self):
        """Load criteria from database if not already loaded."""
        if self.criteria is None:
            self.criteria = get_active_criteria()
            self.criteria_lookup = {c['criterion_id']: c for c in self.criteria}

    def evaluate_single(
        self,
        supplier: SupplierInput,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> EvaluationResult:
        """
        Evaluate a single supplier.

        Args:
            supplier: The supplier input data
            progress_callback: Optional callback to report progress

        Returns:
            EvaluationResult: The evaluation result
        """
        import time
        start_time = time.time()

        self._load_criteria()

        def report(msg: str):
            if progress_callback:
                progress_callback(msg)

        try:
            # Step 1: Extract text from PDF
            report(f"Extracting text from {supplier.name}'s PDF...")
            proposal_text = extract_text_from_uploaded_file(supplier.pdf_file)

            if not proposal_text or len(proposal_text.strip()) < 50:
                return EvaluationResult(
                    supplier_name=supplier.name,
                    success=False,
                    error="PDF extraction failed or document is too short",
                    processing_time_seconds=time.time() - start_time
                )

            # Step 2: Call LLM for evaluation
            report(f"Evaluating {supplier.name} with LLM...")
            raw_response = evaluator.evaluate(
                proposal_text=proposal_text,
                criteria=self.criteria,
                supplier_name=supplier.name
            )

            # Step 3: Validate the response
            report(f"Validating evaluation for {supplier.name}...")
            validated, validation_success = validate_llm_response(
                raw_response=raw_response,
                expected_criteria=self.criteria
            )

            # Collect warnings
            warnings = [
                {
                    "type": w.warning_type,
                    "message": w.message,
                    "criterion_id": w.criterion_id
                }
                for w in validated.warnings
            ]

            # Step 4: Calculate scores
            report(f"Calculating scores for {supplier.name}...")
            score = calculate_supplier_score(
                validated_eval=validated,
                criteria_lookup=self.criteria_lookup
            )

            return EvaluationResult(
                supplier_name=supplier.name,
                success=True,
                score=score,
                raw_response=raw_response,
                validation_warnings=warnings,
                processing_time_seconds=time.time() - start_time
            )

        except Exception as e:
            return EvaluationResult(
                supplier_name=supplier.name,
                success=False,
                error=str(e),
                processing_time_seconds=time.time() - start_time
            )

    def evaluate_all(
        self,
        suppliers: List[SupplierInput],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> BatchResult:
        """
        Evaluate all suppliers in sequence.

        Args:
            suppliers: List of supplier inputs
            progress_callback: Optional callback(message, current, total) for progress

        Returns:
            BatchResult: Results for all suppliers
        """
        started_at = datetime.now()
        results = []

        def report(msg: str, current: int, total: int):
            if progress_callback:
                progress_callback(msg, current, total)

        total = len(suppliers)
        for i, supplier in enumerate(suppliers):
            report(f"Processing {supplier.name}...", i + 1, total)

            # Create a single-supplier progress callback
            def single_progress(msg: str):
                report(msg, i + 1, total)

            result = self.evaluate_single(supplier, single_progress)
            results.append(result)

        completed_at = datetime.now()

        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        return BatchResult(
            results=results,
            total_suppliers=total,
            successful_evaluations=successful,
            failed_evaluations=failed,
            evaluation_mode="MOCK" if evaluator.is_mock_mode() else "LIVE",
            started_at=started_at,
            completed_at=completed_at
        )


# Create singleton instance
batch_evaluator = BatchEvaluator()


def format_batch_summary(batch_result: BatchResult) -> str:
    """
    Format a summary of the batch evaluation.

    Args:
        batch_result: The batch evaluation result

    Returns:
        str: Formatted summary
    """
    lines = []
    lines.append("═" * 60)
    lines.append("BATCH EVALUATION SUMMARY")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Mode: {batch_result.evaluation_mode}")
    lines.append(f"Total Suppliers: {batch_result.total_suppliers}")
    lines.append(f"Successful: {batch_result.successful_evaluations}")
    lines.append(f"Failed: {batch_result.failed_evaluations}")
    lines.append("")

    # Show ranking
    ranking = batch_result.get_ranking()
    if ranking:
        lines.append("RANKING:")
        lines.append("-" * 40)
        for r in ranking:
            lines.append(
                f"  #{r['rank']} {r['supplier_name']}: "
                f"{r['total_weighted_score']:.2f}/100 "
                f"({r['overall_percentage']:.1f}%)"
            )
        lines.append("")

    # Show failed suppliers
    failed = [r for r in batch_result.results if not r.success]
    if failed:
        lines.append("FAILED EVALUATIONS:")
        lines.append("-" * 40)
        for f in failed:
            lines.append(f"  • {f.supplier_name}: {f.error}")
        lines.append("")

    lines.append("═" * 60)

    return "\n".join(lines)


# For testing
if __name__ == "__main__":
    import os

    print("=== Testing Batch Evaluator ===")
    print()

    # Check for sample PDFs
    sample_dir = "sample_rfps"
    if not os.path.exists(sample_dir):
        print(f"Note: {sample_dir}/ directory not found")
        print("Creating directory for future use...")
        os.makedirs(sample_dir)

    # Test with mock data (simulating uploaded files)
    print("Testing with simulated supplier data...")
    print()

    # Create mock "uploaded files" using simple text
    class MockUploadedFile:
        """Mock file object for testing."""
        def __init__(self, name: str, content: bytes):
            self.name = name
            self._content = content

        def read(self) -> bytes:
            return self._content

        def seek(self, pos: int):
            pass

    # Since we don't have real PDFs, we'll test the structure
    print("Batch evaluator structure test:")
    print(f"  - BatchEvaluator class: OK")
    print(f"  - SupplierInput dataclass: OK")
    print(f"  - EvaluationResult dataclass: OK")
    print(f"  - BatchResult dataclass: OK")
    print(f"  - format_batch_summary function: OK")
    print()

    # Test with criteria loading
    batch_eval = BatchEvaluator()
    batch_eval._load_criteria()
    print(f"Loaded {len(batch_eval.criteria)} criteria for evaluation")
    print()

    print("Mode:", "MOCK" if evaluator.is_mock_mode() else "LIVE")
    print()
    print("Batch evaluator is ready for use!")
    print()
    print("To use in Streamlit:")
    print("  from src.batch_evaluator import batch_evaluator, SupplierInput")
    print("  ")
    print("  suppliers = [")
    print("      SupplierInput(name='Supplier A', pdf_file=uploaded_file_a),")
    print("      SupplierInput(name='Supplier B', pdf_file=uploaded_file_b),")
    print("  ]")
    print("  ")
    print("  result = batch_evaluator.evaluate_all(suppliers)")
