"""
Benchmarks Module

Computes comparative statistics across all supplier evaluations.
Calculates best, worst, average, and spread for each criterion.
All calculations are deterministic Python - no LLM involvement.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import statistics

from src.scorer import SupplierScore, CriterionScore


@dataclass
class CriterionBenchmark:
    """Benchmark statistics for a single criterion."""
    criterion_id: int
    name: str
    weight: float
    max_score: int

    # Raw score statistics
    best_raw_score: int
    worst_raw_score: int
    average_raw_score: float
    std_dev_raw: float  # Standard deviation

    # Percentage statistics (0-100)
    best_percentage: float
    worst_percentage: float
    average_percentage: float

    # Which suppliers achieved best/worst
    best_suppliers: List[str] = field(default_factory=list)
    worst_suppliers: List[str] = field(default_factory=list)


@dataclass
class OverallBenchmarks:
    """Complete benchmark data for an evaluation run."""
    criteria_benchmarks: List[CriterionBenchmark]

    # Overall statistics
    best_total_score: float
    worst_total_score: float
    average_total_score: float
    std_dev_total: float

    # Supplier count
    supplier_count: int

    # Top performers
    top_supplier: Optional[str] = None
    bottom_supplier: Optional[str] = None

    def get_benchmark_for_criterion(self, criterion_id: int) -> Optional[CriterionBenchmark]:
        """Get benchmark for a specific criterion."""
        for b in self.criteria_benchmarks:
            if b.criterion_id == criterion_id:
                return b
        return None


def compute_benchmarks(scores: List[SupplierScore]) -> OverallBenchmarks:
    """
    Compute benchmarks from a list of supplier scores.

    Args:
        scores: List of SupplierScore objects from successful evaluations

    Returns:
        OverallBenchmarks: Complete benchmark statistics

    Example:
        from src.benchmarks import compute_benchmarks

        # After batch evaluation
        successful_scores = batch_result.get_successful_scores()
        benchmarks = compute_benchmarks(successful_scores)

        print(f"Best overall: {benchmarks.best_total_score:.2f}")
        print(f"Average: {benchmarks.average_total_score:.2f}")
    """
    if not scores:
        # Return empty benchmarks
        return OverallBenchmarks(
            criteria_benchmarks=[],
            best_total_score=0.0,
            worst_total_score=0.0,
            average_total_score=0.0,
            std_dev_total=0.0,
            supplier_count=0
        )

    # Collect all criterion IDs (assuming all suppliers have same criteria)
    first_score = scores[0]
    criterion_ids = [cs.criterion_id for cs in first_score.criteria_scores]

    # Build criterion benchmarks
    criteria_benchmarks = []

    for cid in criterion_ids:
        # Collect scores for this criterion across all suppliers
        criterion_data = []
        for supplier_score in scores:
            for cs in supplier_score.criteria_scores:
                if cs.criterion_id == cid:
                    criterion_data.append({
                        'supplier': supplier_score.supplier_name,
                        'raw_score': cs.raw_score,
                        'max_score': cs.max_score,
                        'percentage': cs.percentage,
                        'name': cs.name,
                        'weight': cs.weight
                    })
                    break

        if not criterion_data:
            continue

        # Extract values
        raw_scores = [d['raw_score'] for d in criterion_data]
        percentages = [d['percentage'] for d in criterion_data]

        # Get metadata from first entry
        name = criterion_data[0]['name']
        weight = criterion_data[0]['weight']
        max_score = criterion_data[0]['max_score']

        # Calculate statistics
        best_raw = max(raw_scores)
        worst_raw = min(raw_scores)
        avg_raw = statistics.mean(raw_scores)
        std_raw = statistics.stdev(raw_scores) if len(raw_scores) > 1 else 0.0

        best_pct = max(percentages)
        worst_pct = min(percentages)
        avg_pct = statistics.mean(percentages)

        # Find which suppliers achieved best/worst
        best_suppliers = [
            d['supplier'] for d in criterion_data
            if d['raw_score'] == best_raw
        ]
        worst_suppliers = [
            d['supplier'] for d in criterion_data
            if d['raw_score'] == worst_raw
        ]

        benchmark = CriterionBenchmark(
            criterion_id=cid,
            name=name,
            weight=weight,
            max_score=max_score,
            best_raw_score=best_raw,
            worst_raw_score=worst_raw,
            average_raw_score=round(avg_raw, 2),
            std_dev_raw=round(std_raw, 2),
            best_percentage=round(best_pct, 2),
            worst_percentage=round(worst_pct, 2),
            average_percentage=round(avg_pct, 2),
            best_suppliers=best_suppliers,
            worst_suppliers=worst_suppliers
        )
        criteria_benchmarks.append(benchmark)

    # Calculate overall statistics
    total_scores = [s.total_weighted_score for s in scores]

    best_total = max(total_scores)
    worst_total = min(total_scores)
    avg_total = statistics.mean(total_scores)
    std_total = statistics.stdev(total_scores) if len(total_scores) > 1 else 0.0

    # Find top and bottom suppliers
    sorted_scores = sorted(scores, key=lambda s: s.total_weighted_score, reverse=True)
    top_supplier = sorted_scores[0].supplier_name if sorted_scores else None
    bottom_supplier = sorted_scores[-1].supplier_name if sorted_scores else None

    return OverallBenchmarks(
        criteria_benchmarks=criteria_benchmarks,
        best_total_score=round(best_total, 2),
        worst_total_score=round(worst_total, 2),
        average_total_score=round(avg_total, 2),
        std_dev_total=round(std_total, 2),
        supplier_count=len(scores),
        top_supplier=top_supplier,
        bottom_supplier=bottom_supplier
    )


def format_benchmarks_summary(benchmarks: OverallBenchmarks) -> str:
    """
    Format benchmarks for display.

    Args:
        benchmarks: The computed benchmarks

    Returns:
        str: Formatted summary
    """
    lines = []
    lines.append("═" * 60)
    lines.append("BENCHMARK SUMMARY")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Suppliers Evaluated: {benchmarks.supplier_count}")
    lines.append("")
    lines.append("OVERALL SCORES:")
    lines.append(f"  Best:    {benchmarks.best_total_score:.2f}/100 ({benchmarks.top_supplier})")
    lines.append(f"  Worst:   {benchmarks.worst_total_score:.2f}/100 ({benchmarks.bottom_supplier})")
    lines.append(f"  Average: {benchmarks.average_total_score:.2f}/100")
    lines.append(f"  Spread:  {benchmarks.std_dev_total:.2f} (std dev)")
    lines.append("")
    lines.append("PER-CRITERION BENCHMARKS:")
    lines.append("-" * 60)

    for cb in benchmarks.criteria_benchmarks:
        lines.append(f"")
        lines.append(f"  {cb.name} (Weight: {cb.weight}%)")
        lines.append(f"    Best:  {cb.best_raw_score}/{cb.max_score} ({cb.best_percentage:.0f}%) - {', '.join(cb.best_suppliers)}")
        lines.append(f"    Worst: {cb.worst_raw_score}/{cb.max_score} ({cb.worst_percentage:.0f}%) - {', '.join(cb.worst_suppliers)}")
        lines.append(f"    Avg:   {cb.average_raw_score}/{cb.max_score} ({cb.average_percentage:.0f}%)")

    lines.append("")
    lines.append("═" * 60)

    return "\n".join(lines)


def get_supplier_vs_benchmark(
    supplier_score: SupplierScore,
    benchmarks: OverallBenchmarks
) -> Dict[str, Any]:
    """
    Compare a supplier's scores against benchmarks.

    Args:
        supplier_score: The supplier's score
        benchmarks: The computed benchmarks

    Returns:
        dict: Comparison data showing above/below average for each criterion
    """
    comparisons = []

    for cs in supplier_score.criteria_scores:
        benchmark = benchmarks.get_benchmark_for_criterion(cs.criterion_id)
        if benchmark is None:
            continue

        diff_from_avg = cs.percentage - benchmark.average_percentage
        diff_from_best = cs.percentage - benchmark.best_percentage

        # Determine status
        if cs.raw_score == benchmark.best_raw_score:
            status = "BEST"
        elif cs.raw_score == benchmark.worst_raw_score:
            status = "WORST"
        elif diff_from_avg > 5:
            status = "ABOVE_AVG"
        elif diff_from_avg < -5:
            status = "BELOW_AVG"
        else:
            status = "AVERAGE"

        comparisons.append({
            "criterion_id": cs.criterion_id,
            "name": cs.name,
            "score": cs.raw_score,
            "max_score": cs.max_score,
            "percentage": round(cs.percentage, 2),
            "benchmark_avg": benchmark.average_percentage,
            "benchmark_best": benchmark.best_percentage,
            "diff_from_avg": round(diff_from_avg, 2),
            "diff_from_best": round(diff_from_best, 2),
            "status": status
        })

    # Overall comparison
    overall_diff = supplier_score.total_weighted_score - benchmarks.average_total_score

    return {
        "supplier_name": supplier_score.supplier_name,
        "total_score": round(supplier_score.total_weighted_score, 2),
        "benchmark_avg": benchmarks.average_total_score,
        "benchmark_best": benchmarks.best_total_score,
        "diff_from_avg": round(overall_diff, 2),
        "criteria_comparisons": comparisons
    }


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score

    print("=== Testing Benchmarks ===")
    print()

    # Get criteria
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    # Create mock supplier scores
    sample_proposals = [
        ("Alpha Corp", "We offer enterprise solutions with 15 years experience. SOC 2 certified. 24/7 support. Competitive pricing at $450,000."),
        ("Beta Inc", "Modern cloud-native architecture. Agile implementation. ISO 27001 certified. Premium pricing at $600,000 with full support."),
        ("Gamma Ltd", "Cost-effective solution at $300,000. Basic support package. 5 years experience. Standard security compliance."),
    ]

    print("Evaluating 3 mock suppliers...")
    print()

    scores = []
    for name, proposal in sample_proposals:
        raw = evaluator.evaluate(proposal, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)
        print(f"  {name}: {score.total_weighted_score:.2f}/100")

    print()

    # Compute benchmarks
    benchmarks = compute_benchmarks(scores)

    print(format_benchmarks_summary(benchmarks))
    print()

    # Show comparison for first supplier
    print("Supplier vs Benchmark (Alpha Corp):")
    comparison = get_supplier_vs_benchmark(scores[0], benchmarks)
    for c in comparison['criteria_comparisons']:
        status_icon = {
            'BEST': '★',
            'WORST': '✗',
            'ABOVE_AVG': '↑',
            'BELOW_AVG': '↓',
            'AVERAGE': '='
        }.get(c['status'], '?')
        print(f"  {status_icon} {c['name']}: {c['percentage']:.0f}% (avg: {c['benchmark_avg']:.0f}%, diff: {c['diff_from_avg']:+.0f}%)")
