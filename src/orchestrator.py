"""
Orchestrator Module

Runs the complete RFP evaluation pipeline:
1. PDF Text Extraction
2. LLM Evaluation (or Mock)
3. Response Validation
4. Weighted Scoring
5. Benchmark Computation
6. Gap Analysis
7. Relative Performance
8. PPI Calculation
9. Final Ranking

This is the main entry point for running evaluations.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.errors import (
    RFPEvaluationError,
    PDFExtractionError,
    PDFTooShortError,
    LLMError,
    ValidationError,
    NoSuppliersError,
    AllSuppliersFailedError,
    PipelineError
)

# Import all pipeline components
from src.database import get_active_criteria
from src.pdf_tool import extract_text_from_uploaded_file
from src.evaluator import evaluator
from src.validator import validate_llm_response
from src.scorer import calculate_supplier_score, SupplierScore
from src.benchmarks import compute_benchmarks, OverallBenchmarks
from src.gaps import analyze_supplier_gaps, SupplierGapAnalysis
from src.relative_performance import calculate_relative_performance, SupplierRelativePerformance
from src.ppi import calculate_ppi, PPIBreakdown
from src.ranking import rank_suppliers, RankingResult


@dataclass
class SupplierInput:
    """Input data for a supplier evaluation."""
    name: str
    pdf_file: Any  # Streamlit UploadedFile or file-like object
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupplierResult:
    """Complete evaluation result for a single supplier."""
    supplier_name: str
    success: bool

    # Core results
    score: Optional[SupplierScore] = None
    ppi: Optional[PPIBreakdown] = None
    gaps: Optional[SupplierGapAnalysis] = None
    relative: Optional[SupplierRelativePerformance] = None

    # Raw data
    extracted_text: Optional[str] = None
    raw_llm_response: Optional[Dict[str, Any]] = None
    validation_warnings: List[Dict[str, Any]] = field(default_factory=list)

    # Error info
    error: Optional[str] = None
    error_stage: Optional[str] = None  # Which stage failed

    # Timing
    processing_time_seconds: float = 0.0


@dataclass
class PipelineResult:
    """Complete result of running the evaluation pipeline."""
    # Individual results
    supplier_results: List[SupplierResult]

    # Aggregate analysis
    benchmarks: Optional[OverallBenchmarks] = None
    ranking: Optional[RankingResult] = None

    # Metadata
    run_id: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    evaluation_mode: str = "MOCK"

    # Summary stats
    total_suppliers: int = 0
    successful_evaluations: int = 0
    failed_evaluations: int = 0

    def get_winner(self) -> Optional[SupplierResult]:
        """Get the winning supplier result."""
        if self.ranking and self.ranking.rankings:
            winner_name = self.ranking.rankings[0].supplier_name
            for r in self.supplier_results:
                if r.supplier_name == winner_name:
                    return r
        return None

    def get_successful_results(self) -> List[SupplierResult]:
        """Get all successful supplier results."""
        return [r for r in self.supplier_results if r.success]


class Orchestrator:
    """
    Orchestrates the complete RFP evaluation pipeline.

    Usage:
        from src.orchestrator import Orchestrator, SupplierInput

        orch = Orchestrator()

        suppliers = [
            SupplierInput(name="Vendor A", pdf_file=file_a),
            SupplierInput(name="Vendor B", pdf_file=file_b),
        ]

        result = orch.run(suppliers)

        winner = result.get_winner()
        print(f"Winner: {winner.supplier_name}")
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.criteria = None
        self.criteria_lookup = None

    def _load_criteria(self):
        """Load evaluation criteria from database."""
        if self.criteria is None:
            self.criteria = get_active_criteria()
            self.criteria_lookup = {c['criterion_id']: c for c in self.criteria}

    def run(
        self,
        suppliers: List[SupplierInput],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> PipelineResult:
        """
        Run the complete evaluation pipeline.

        Args:
            suppliers: List of supplier inputs
            progress_callback: Optional callback(message, current, total)

        Returns:
            PipelineResult: Complete evaluation results
        """
        started_at = datetime.now()

        # Validate inputs
        if not suppliers:
            raise NoSuppliersError()

        self._load_criteria()

        def report(msg: str, current: int = 0, total: int = 0):
            if progress_callback:
                progress_callback(msg, current, total)

        total = len(suppliers)
        report(f"Starting evaluation of {total} suppliers...", 0, total)

        # Stage 1: Evaluate each supplier
        supplier_results = []
        successful_scores = []

        for i, supplier in enumerate(suppliers):
            report(f"Processing {supplier.name}...", i + 1, total)
            result = self._evaluate_supplier(supplier, report, i + 1, total)
            supplier_results.append(result)

            if result.success and result.score:
                successful_scores.append(result.score)

        # Stage 2: Compute benchmarks (if we have successful evaluations)
        benchmarks = None
        if successful_scores:
            report("Computing benchmarks...", total, total)
            benchmarks = compute_benchmarks(successful_scores)

        # Stage 3: Calculate relative performance
        if successful_scores:
            report("Calculating relative performance...", total, total)
            relative_perfs = calculate_relative_performance(successful_scores)

            # Attach relative performance to results
            rel_lookup = {r.supplier_name: r for r in relative_perfs}
            for result in supplier_results:
                if result.success and result.supplier_name in rel_lookup:
                    result.relative = rel_lookup[result.supplier_name]

        # Stage 4: Calculate gaps (with benchmarks)
        if successful_scores and benchmarks:
            report("Analyzing gaps...", total, total)
            for result in supplier_results:
                if result.success and result.score:
                    result.gaps = analyze_supplier_gaps(result.score, benchmarks)

        # Stage 5: Final ranking
        ranking = None
        if successful_scores:
            report("Computing final ranking...", total, total)
            ranking = rank_suppliers(successful_scores)

        completed_at = datetime.now()

        return PipelineResult(
            supplier_results=supplier_results,
            benchmarks=benchmarks,
            ranking=ranking,
            started_at=started_at,
            completed_at=completed_at,
            evaluation_mode="MOCK" if evaluator.is_mock_mode() else "LIVE",
            total_suppliers=total,
            successful_evaluations=len(successful_scores),
            failed_evaluations=total - len(successful_scores)
        )

    def _evaluate_supplier(
        self,
        supplier: SupplierInput,
        report: Callable,
        current: int,
        total: int
    ) -> SupplierResult:
        """Evaluate a single supplier through the pipeline."""
        import time
        start_time = time.time()

        result = SupplierResult(
            supplier_name=supplier.name,
            success=False
        )

        try:
            # Stage 1: Extract PDF text
            report(f"[{supplier.name}] Extracting PDF text...", current, total)
            extracted_text = extract_text_from_uploaded_file(supplier.pdf_file)
            result.extracted_text = extracted_text

            if not extracted_text or len(extracted_text.strip()) < 50:
                char_count = len(extracted_text.strip()) if extracted_text else 0
                result.error = f"PDF too short ({char_count} chars, minimum 50 required)"
                result.error_stage = "pdf_extraction"
                result.processing_time_seconds = time.time() - start_time
                return result

            # Stage 2: LLM Evaluation
            report(f"[{supplier.name}] Running LLM evaluation...", current, total)
            raw_response = evaluator.evaluate(
                proposal_text=extracted_text,
                criteria=self.criteria,
                supplier_name=supplier.name
            )
            result.raw_llm_response = raw_response

            # Stage 3: Validate response
            report(f"[{supplier.name}] Validating response...", current, total)
            validated, validation_success = validate_llm_response(
                raw_response=raw_response,
                expected_criteria=self.criteria
            )

            result.validation_warnings = [
                {"type": w.warning_type, "message": w.message, "criterion_id": w.criterion_id}
                for w in validated.warnings
            ]

            # Stage 4: Calculate scores
            report(f"[{supplier.name}] Calculating scores...", current, total)
            score = calculate_supplier_score(
                validated_eval=validated,
                criteria_lookup=self.criteria_lookup
            )
            result.score = score

            # Stage 5: Calculate PPI
            report(f"[{supplier.name}] Calculating PPI...", current, total)
            ppi = calculate_ppi(score)
            result.ppi = ppi

            result.success = True
            result.processing_time_seconds = time.time() - start_time
            return result

        except PDFExtractionError as e:
            result.error = e.message
            result.error_stage = "pdf_extraction"
            result.processing_time_seconds = time.time() - start_time
            return result
        except LLMError as e:
            result.error = e.message
            result.error_stage = "llm_evaluation"
            result.processing_time_seconds = time.time() - start_time
            return result
        except ValidationError as e:
            result.error = e.message
            result.error_stage = "validation"
            result.processing_time_seconds = time.time() - start_time
            return result
        except Exception as e:
            result.error = str(e)
            result.error_stage = "unknown"
            result.processing_time_seconds = time.time() - start_time
            return result


# Create singleton instance
orchestrator = Orchestrator()


def format_pipeline_summary(result: PipelineResult) -> str:
    """
    Format a summary of the pipeline result.

    Args:
        result: The pipeline result

    Returns:
        str: Formatted summary
    """
    lines = []
    lines.append("═" * 70)
    lines.append("RFP EVALUATION PIPELINE RESULTS")
    lines.append("═" * 70)
    lines.append("")

    # Metadata
    duration = (result.completed_at - result.started_at).total_seconds() if result.completed_at else 0
    lines.append(f"Mode: {result.evaluation_mode}")
    lines.append(f"Duration: {duration:.2f} seconds")
    lines.append(f"Suppliers: {result.successful_evaluations}/{result.total_suppliers} successful")
    lines.append("")

    # Winner
    if result.ranking and result.ranking.rankings:
        winner = result.ranking.rankings[0]
        lines.append("🏆 WINNER:")
        lines.append(f"   {winner.supplier_name}")
        lines.append(f"   Score: {winner.weighted_score:.2f}/100")
        lines.append(f"   PPI: {winner.ppi_score:.2f}/100")
        lines.append("")

    # Full ranking
    if result.ranking:
        lines.append("FINAL RANKING:")
        lines.append("-" * 50)
        for r in result.ranking.rankings:
            marker = "🏆" if r.rank == 1 else "  "
            lines.append(f"   {marker} #{r.rank} {r.supplier_name}: {r.weighted_score:.2f}")
        lines.append("")

    # Benchmarks summary
    if result.benchmarks:
        lines.append("BENCHMARK SUMMARY:")
        lines.append(f"   Best Score: {result.benchmarks.best_total_score:.2f}")
        lines.append(f"   Average: {result.benchmarks.average_total_score:.2f}")
        lines.append(f"   Worst: {result.benchmarks.worst_total_score:.2f}")
        lines.append("")

    # Failed evaluations
    failed = [r for r in result.supplier_results if not r.success]
    if failed:
        lines.append("FAILED EVALUATIONS:")
        for f in failed:
            lines.append(f"   ✗ {f.supplier_name}: {f.error} (at {f.error_stage})")
        lines.append("")

    lines.append("═" * 70)

    return "\n".join(lines)


# For testing
if __name__ == "__main__":
    print("=== Testing Orchestrator ===")
    print()

    # Create mock uploaded files (simulating Streamlit uploads)
    class MockUploadedFile:
        """Mock file for testing."""
        def __init__(self, name: str, content: str):
            self.name = name
            self._content = content.encode()

        def read(self) -> bytes:
            return self._content

        def seek(self, pos: int):
            pass

    # Create sample proposals
    proposals = [
        ("TechCorp Solutions", """
        PROPOSAL FOR RFP-2024-001

        Technical Approach:
        We propose a modern microservices architecture with Kubernetes orchestration.
        Our team has 15 years of experience in enterprise software development.

        Implementation Timeline:
        - Phase 1 (Months 1-2): Requirements and Design
        - Phase 2 (Months 3-5): Core Development
        - Phase 3 (Month 6): Testing and Deployment

        Pricing:
        Total project cost: $450,000
        Annual maintenance: $50,000

        Security:
        - SOC 2 Type II certified
        - ISO 27001 compliant
        - Regular penetration testing

        Support:
        - 24/7 support hotline
        - Dedicated account manager
        - 4-hour SLA for critical issues
        """),

        ("CloudFirst Inc", """
        PROPOSAL FOR RFP-2024-001

        Technical Solution:
        Cloud-native solution built on AWS with serverless components.
        5 years focused experience in cloud migrations.

        Project Plan:
        - Discovery: 2 weeks
        - Development: 4 months
        - UAT: 1 month

        Investment:
        Implementation: $380,000
        Monthly operations: $5,000

        Compliance:
        - AWS Well-Architected certified
        - Basic security controls

        Customer Success:
        - Email support
        - Monthly check-ins
        """),

        ("BudgetTech Ltd", """
        PROPOSAL

        We offer basic solution.
        New company, 1 year experience.
        Price: $200,000
        Email support only.
        """),
    ]

    # Note: Since these are text strings, not actual PDFs,
    # the PDF extraction will fail. We'll use direct text evaluation instead.
    print("Note: Using direct text evaluation (not PDF) for testing")
    print()

    # Test with direct evaluation (bypassing PDF)
    from src.scorer import calculate_supplier_score
    from src.validator import validate_llm_response
    from src.benchmarks import compute_benchmarks
    from src.ranking import rank_suppliers

    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    scores = []
    for name, text in proposals:
        raw = evaluator.evaluate(text, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)
        print(f"  {name}: {score.total_weighted_score:.2f}")

    print()

    # Compute full analysis
    benchmarks = compute_benchmarks(scores)
    ranking = rank_suppliers(scores)

    # Create a mock pipeline result for display
    result = PipelineResult(
        supplier_results=[],
        benchmarks=benchmarks,
        ranking=ranking,
        evaluation_mode="MOCK",
        total_suppliers=len(proposals),
        successful_evaluations=len(proposals),
        failed_evaluations=0,
        completed_at=datetime.now()
    )

    print(format_pipeline_summary(result))
