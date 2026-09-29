"""
Export Module

Exports evaluation results to JSON format for external use.
Supports full reports, individual scorecards, and summary exports.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.orchestrator import PipelineResult, SupplierResult
from src.scorer import SupplierScore
from src.ppi import PPIBreakdown
from src.gaps import SupplierGapAnalysis
from src.relative_performance import SupplierRelativePerformance
from src.benchmarks import OverallBenchmarks
from src.ranking import RankingResult


def export_full_report(result: PipelineResult) -> Dict[str, Any]:
    """
    Export complete evaluation report as JSON-serializable dict.

    Args:
        result: The PipelineResult from orchestrator

    Returns:
        dict: Complete report data

    Example:
        report = export_full_report(pipeline_result)
        with open('report.json', 'w') as f:
            json.dump(report, f, indent=2)
    """
    return {
        "report_type": "full_evaluation",
        "generated_at": datetime.now().isoformat(),
        "metadata": {
            "evaluation_mode": result.evaluation_mode,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_suppliers": result.total_suppliers,
            "successful_evaluations": result.successful_evaluations,
            "failed_evaluations": result.failed_evaluations
        },
        "ranking": _export_ranking(result.ranking) if result.ranking else None,
        "benchmarks": _export_benchmarks(result.benchmarks) if result.benchmarks else None,
        "suppliers": [
            _export_supplier_result(sr) for sr in result.supplier_results
        ]
    }


def export_summary(result: PipelineResult) -> Dict[str, Any]:
    """
    Export summary report (without detailed justifications).

    Args:
        result: The PipelineResult from orchestrator

    Returns:
        dict: Summary data
    """
    summary = {
        "report_type": "summary",
        "generated_at": datetime.now().isoformat(),
        "evaluation_mode": result.evaluation_mode,
        "total_suppliers": result.total_suppliers
    }

    # Winner info
    if result.ranking and result.ranking.rankings:
        winner = result.ranking.rankings[0]
        summary["winner"] = {
            "name": winner.supplier_name,
            "score": winner.weighted_score,
            "ppi": winner.ppi_score,
            "grade": winner.ppi_breakdown.ppi_grade if winner.ppi_breakdown else None
        }

    # Rankings
    if result.ranking:
        summary["rankings"] = [
            {
                "rank": r.rank,
                "supplier": r.supplier_name,
                "score": r.weighted_score,
                "ppi": r.ppi_score
            }
            for r in result.ranking.rankings
        ]

    # Benchmarks
    if result.benchmarks:
        summary["benchmarks"] = {
            "best": result.benchmarks.best_total_score,
            "average": result.benchmarks.average_total_score,
            "worst": result.benchmarks.worst_total_score
        }

    return summary


def export_supplier_scorecard(supplier_result: SupplierResult) -> Dict[str, Any]:
    """
    Export individual supplier scorecard.

    Args:
        supplier_result: The SupplierResult

    Returns:
        dict: Scorecard data
    """
    return {
        "report_type": "supplier_scorecard",
        "generated_at": datetime.now().isoformat(),
        "supplier": _export_supplier_result(supplier_result)
    }


def _export_supplier_result(sr: SupplierResult) -> Dict[str, Any]:
    """Export a single supplier result."""
    data = {
        "supplier_name": sr.supplier_name,
        "success": sr.success,
        "processing_time_seconds": sr.processing_time_seconds
    }

    if not sr.success:
        data["error"] = sr.error
        data["error_stage"] = sr.error_stage
        return data

    # Score breakdown
    if sr.score:
        data["score"] = _export_score(sr.score)

    # PPI
    if sr.ppi:
        data["ppi"] = _export_ppi(sr.ppi)

    # Gaps
    if sr.gaps:
        data["gaps"] = _export_gaps(sr.gaps)

    # Relative performance
    if sr.relative:
        data["relative_performance"] = _export_relative(sr.relative)

    # Validation warnings
    if sr.validation_warnings:
        data["validation_warnings"] = sr.validation_warnings

    return data


def _export_score(score: SupplierScore) -> Dict[str, Any]:
    """Export score data."""
    return {
        "total_weighted_score": round(score.total_weighted_score, 2),
        "total_raw_score": score.total_raw_score,
        "total_max_score": score.total_max_score,
        "overall_percentage": round(score.overall_percentage, 2),
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
        ],
        "risks": score.risks,
        "overall_summary": score.overall_summary
    }


def _export_ppi(ppi: PPIBreakdown) -> Dict[str, Any]:
    """Export PPI data."""
    return {
        "ppi_score": round(ppi.ppi_score, 2),
        "ppi_grade": ppi.ppi_grade,
        "weighted_score": round(ppi.weighted_score, 2),
        "consistency_score": round(ppi.consistency_score, 2),
        "quality_score": round(ppi.quality_score, 2),
        "risk_penalty": round(ppi.risk_penalty, 2),
        "risk_count": ppi.risk_count,
        "warning_count": ppi.warning_count
    }


def _export_gaps(gaps: SupplierGapAnalysis) -> Dict[str, Any]:
    """Export gaps analysis."""
    return {
        "total_gap_count": gaps.total_gap_count,
        "max_potential_improvement": round(gaps.max_potential_improvement, 2),
        "critical_gaps": [
            {"name": g.name, "percentage": g.percentage, "gap_to_threshold": g.gap_to_threshold}
            for g in gaps.critical_gaps
        ],
        "high_gaps": [
            {"name": g.name, "percentage": g.percentage, "gap_to_threshold": g.gap_to_threshold}
            for g in gaps.high_gaps
        ],
        "medium_gaps": [
            {"name": g.name, "percentage": g.percentage}
            for g in gaps.medium_gaps
        ]
    }


def _export_relative(rel: SupplierRelativePerformance) -> Dict[str, Any]:
    """Export relative performance."""
    return {
        "rank": rel.rank,
        "total_suppliers": rel.total_suppliers,
        "percentile": round(rel.percentile, 2),
        "tier": rel.tier.value,
        "normalized_score": round(rel.normalized_score, 2),
        "distance_from_leader": round(rel.distance_from_leader, 2),
        "distance_from_avg": round(rel.distance_from_avg, 2),
        "relative_strengths": rel.relative_strengths,
        "relative_weaknesses": rel.relative_weaknesses
    }


def _export_ranking(ranking: RankingResult) -> Dict[str, Any]:
    """Export ranking data."""
    return {
        "total_suppliers": ranking.total_suppliers,
        "ties_encountered": ranking.ties_encountered,
        "tie_break_methods_used": ranking.tie_break_methods_used,
        "rankings": [
            {
                "rank": r.rank,
                "supplier_name": r.supplier_name,
                "weighted_score": round(r.weighted_score, 2),
                "ppi_score": round(r.ppi_score, 2),
                "risk_count": r.risk_count,
                "warning_count": r.warning_count,
                "rank_status": r.rank_status.value,
                "tied_with": r.tied_with
            }
            for r in ranking.rankings
        ]
    }


def _export_benchmarks(bench: OverallBenchmarks) -> Dict[str, Any]:
    """Export benchmarks data."""
    return {
        "supplier_count": bench.supplier_count,
        "best_total_score": round(bench.best_total_score, 2),
        "worst_total_score": round(bench.worst_total_score, 2),
        "average_total_score": round(bench.average_total_score, 2),
        "std_dev_total": round(bench.std_dev_total, 2),
        "top_supplier": bench.top_supplier,
        "bottom_supplier": bench.bottom_supplier,
        "criteria_benchmarks": [
            {
                "criterion_id": cb.criterion_id,
                "name": cb.name,
                "weight": cb.weight,
                "best_raw_score": cb.best_raw_score,
                "worst_raw_score": cb.worst_raw_score,
                "average_raw_score": cb.average_raw_score,
                "best_suppliers": cb.best_suppliers,
                "worst_suppliers": cb.worst_suppliers
            }
            for cb in bench.criteria_benchmarks
        ]
    }


def to_json_string(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Convert export data to JSON string.

    Args:
        data: The export data dict
        indent: JSON indentation level

    Returns:
        str: JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


# For testing
if __name__ == "__main__":
    from src.database import get_active_criteria
    from src.evaluator import evaluator
    from src.validator import validate_llm_response
    from src.scorer import calculate_supplier_score
    from src.benchmarks import compute_benchmarks
    from src.gaps import analyze_supplier_gaps
    from src.relative_performance import calculate_relative_performance
    from src.ppi import calculate_ppi
    from src.ranking import rank_suppliers

    print("=== Testing JSON Export ===")
    print()

    # Create mock evaluation
    criteria = get_active_criteria()
    criteria_lookup = {c['criterion_id']: c for c in criteria}

    proposals = [
        ("TechCorp", "Enterprise solution with modern architecture. SOC 2 certified."),
        ("BudgetCo", "Basic solution at low cost. Limited features."),
    ]

    scores = []
    for name, text in proposals:
        raw = evaluator.evaluate(text, criteria, name)
        validated, _ = validate_llm_response(raw, criteria)
        score = calculate_supplier_score(validated, criteria_lookup)
        scores.append(score)

    benchmarks = compute_benchmarks(scores)
    ranking = rank_suppliers(scores)

    # Create mock PipelineResult
    from src.orchestrator import PipelineResult, SupplierResult
    supplier_results = []
    relatives = calculate_relative_performance(scores)

    for i, score in enumerate(scores):
        ppi = calculate_ppi(score)
        gaps = analyze_supplier_gaps(score, benchmarks)
        rel = relatives[i] if i < len(relatives) else None

        sr = SupplierResult(
            supplier_name=score.supplier_name,
            success=True,
            score=score,
            ppi=ppi,
            gaps=gaps,
            relative=rel,
            validation_warnings=[]
        )
        supplier_results.append(sr)

    result = PipelineResult(
        supplier_results=supplier_results,
        benchmarks=benchmarks,
        ranking=ranking,
        evaluation_mode="MOCK",
        total_suppliers=2,
        successful_evaluations=2,
        failed_evaluations=0
    )

    # Test exports
    print("1. Full Report Export:")
    full_report = export_full_report(result)
    print(f"   Keys: {list(full_report.keys())}")
    print(f"   Suppliers: {len(full_report['suppliers'])}")

    print()
    print("2. Summary Export:")
    summary = export_summary(result)
    print(f"   Winner: {summary.get('winner', {}).get('name')}")

    print()
    print("3. JSON String (first 500 chars):")
    json_str = to_json_string(summary)
    print(json_str[:500] + "...")

    print()
    print("Export module ready!")
