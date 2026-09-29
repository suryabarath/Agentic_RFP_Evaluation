"""
Database Helper Functions

This module provides simple functions to interact with the SQLite database.
Other parts of the application use these functions instead of writing SQL directly.
"""

import sqlite3
import os
import json
from typing import List, Dict, Optional, Any


def get_db_path() -> str:
    """
    Get the path to the database file.

    Returns:
        str: Full path to rfp.db
    """
    # Go up one level from src/ to project root, then into database/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'database', 'rfp.db')


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return a database connection.

    The connection uses Row factory so we can access columns by name.
    Example: row['name'] instead of row[0]

    Returns:
        sqlite3.Connection: A connection to the database
    """
    db_path = get_db_path()

    # Check if database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            "Please run 'python database/init_db.py' first."
        )

    # Create connection with Row factory for easier column access
    # timeout=30 prevents "database is locked" errors in concurrent access
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def get_active_criteria() -> List[Dict[str, Any]]:
    """
    Fetch all active evaluation criteria from the database.

    Returns:
        List of dictionaries, each containing:
        - criterion_id: int
        - name: str
        - description: str
        - weight: float
        - max_score: int

    Example:
        criteria = get_active_criteria()
        for c in criteria:
            print(f"{c['name']}: {c['weight']}%")
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT criterion_id, name, description, weight, max_score
        FROM evaluation_criteria
        WHERE is_active = 1
        ORDER BY criterion_id
    """)

    # Convert Row objects to dictionaries
    rows = cursor.fetchall()
    criteria = [dict(row) for row in rows]

    conn.close()
    return criteria


def get_total_weight() -> float:
    """
    Calculate the total weight of all active criteria.

    Returns:
        float: Sum of all weights (should be 100.0)
    """
    criteria = get_active_criteria()
    return sum(c['weight'] for c in criteria)


def create_rfp_run(notes: Optional[str] = None) -> int:
    """
    Create a new RFP evaluation run.

    Args:
        notes: Optional description or notes for this run

    Returns:
        int: The rfp_run_id of the newly created run

    Example:
        run_id = create_rfp_run("Evaluating Q4 suppliers")
        print(f"Created run with ID: {run_id}")
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO rfp_runs (status, notes)
        VALUES ('pending', ?)
    """, (notes,))

    # Get the ID of the row we just inserted
    run_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return run_id


def update_rfp_run_status(rfp_run_id: int, status: str) -> None:
    """
    Update the status of an RFP run.

    Args:
        rfp_run_id: The ID of the run to update
        status: New status ('pending', 'in_progress', 'completed', 'failed')

    Example:
        update_rfp_run_status(1, 'completed')
    """
    valid_statuses = ['pending', 'in_progress', 'completed', 'failed']

    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE rfp_runs
        SET status = ?
        WHERE rfp_run_id = ?
    """, (status, rfp_run_id))

    conn.commit()
    conn.close()


def save_supplier_result(
    rfp_run_id: int,
    supplier_name: str,
    submission_date: str,
    experience_rating: int,
    absolute_score: float,
    ppi: float,
    final_rank: int,
    result_json: Dict[str, Any],
    validation_warnings: Optional[List[str]] = None
) -> int:
    """
    Save the evaluation result for one supplier.

    Args:
        rfp_run_id: The ID of the evaluation run
        supplier_name: Name of the supplier
        submission_date: Date of submission (YYYY-MM-DD format)
        experience_rating: Historical experience rating (1-10)
        absolute_score: Weighted score (0-100)
        ppi: Peer Performance Index
        final_rank: Final ranking position (1, 2, 3, etc.)
        result_json: Full evaluation result as a dictionary
        validation_warnings: List of any validation warnings

    Returns:
        int: The result_id of the saved record

    Example:
        result_id = save_supplier_result(
            rfp_run_id=1,
            supplier_name="Apex Systems",
            submission_date="2024-01-15",
            experience_rating=8,
            absolute_score=82.5,
            ppi=95.2,
            final_rank=1,
            result_json={"criteria": [...], "risks": [...]},
            validation_warnings=["Minor: score rounded"]
        )
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Convert result_json dict to JSON string
    result_json_str = json.dumps(result_json)

    # Convert warnings list to JSON string (or None if empty)
    warnings_str = json.dumps(validation_warnings) if validation_warnings else None

    cursor.execute("""
        INSERT INTO supplier_results (
            rfp_run_id,
            supplier_name,
            submission_date,
            experience_rating,
            absolute_score,
            ppi,
            final_rank,
            result_json,
            validation_warnings
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rfp_run_id,
        supplier_name,
        submission_date,
        experience_rating,
        absolute_score,
        ppi,
        final_rank,
        result_json_str,
        warnings_str
    ))

    result_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return result_id


def get_run_results(rfp_run_id: int) -> List[Dict[str, Any]]:
    """
    Get all supplier results for a specific RFP run.

    Args:
        rfp_run_id: The ID of the run

    Returns:
        List of dictionaries containing supplier results,
        ordered by final_rank (best first)

    Example:
        results = get_run_results(1)
        for r in results:
            print(f"Rank {r['final_rank']}: {r['supplier_name']}")
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            result_id,
            rfp_run_id,
            supplier_name,
            submission_date,
            experience_rating,
            absolute_score,
            ppi,
            final_rank,
            result_json,
            validation_warnings,
            created_at
        FROM supplier_results
        WHERE rfp_run_id = ?
        ORDER BY final_rank ASC
    """, (rfp_run_id,))

    rows = cursor.fetchall()
    results = []

    for row in rows:
        result = dict(row)
        # Parse JSON strings back to Python objects
        result['result_json'] = json.loads(result['result_json'])
        if result['validation_warnings']:
            result['validation_warnings'] = json.loads(result['validation_warnings'])
        results.append(result)

    conn.close()
    return results


def get_rfp_run(rfp_run_id: int) -> Optional[Dict[str, Any]]:
    """
    Get details of a specific RFP run.

    Args:
        rfp_run_id: The ID of the run

    Returns:
        Dictionary with run details, or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rfp_run_id, created_at, status, notes
        FROM rfp_runs
        WHERE rfp_run_id = ?
    """, (rfp_run_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_all_runs() -> List[Dict[str, Any]]:
    """
    Get all RFP evaluation runs.

    Returns:
        List of dictionaries with run details, newest first
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.rfp_run_id,
            r.created_at,
            r.status,
            r.notes,
            COUNT(s.result_id) as supplier_count,
            MIN(s.final_rank) as winner_rank
        FROM rfp_runs r
        LEFT JOIN supplier_results s ON r.rfp_run_id = s.rfp_run_id
        GROUP BY r.rfp_run_id
        ORDER BY r.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def save_pipeline_result(
    pipeline_result,
    notes: Optional[str] = None
) -> int:
    """
    Save a complete PipelineResult to the database.

    Args:
        pipeline_result: The PipelineResult from orchestrator
        notes: Optional notes for this run

    Returns:
        int: The rfp_run_id of the saved run

    Example:
        from src.orchestrator import orchestrator
        result = orchestrator.run(suppliers)
        run_id = save_pipeline_result(result, "Q4 2024 Evaluation")
    """
    from datetime import datetime

    # Create the run record
    run_id = create_rfp_run(notes)

    # Update status to in_progress
    update_rfp_run_status(run_id, 'in_progress')

    try:
        # Save each supplier result
        for supplier_result in pipeline_result.supplier_results:
            if not supplier_result.success:
                # Save failed evaluation with minimal data
                _save_failed_result(run_id, supplier_result)
                continue

            # Get rank from ranking result
            rank = 0
            if pipeline_result.ranking:
                for ranked in pipeline_result.ranking.rankings:
                    if ranked.supplier_name == supplier_result.supplier_name:
                        rank = ranked.rank
                        break

            # Build comprehensive result JSON
            result_json = _build_result_json(supplier_result, pipeline_result)

            # Get validation warnings as list of strings
            warnings = [
                f"[{w['type']}] {w['message']}"
                for w in supplier_result.validation_warnings
            ]

            # Save the result
            save_supplier_result(
                rfp_run_id=run_id,
                supplier_name=supplier_result.supplier_name,
                submission_date=datetime.now().strftime('%Y-%m-%d'),
                experience_rating=0,  # Not used in current implementation
                absolute_score=supplier_result.score.total_weighted_score if supplier_result.score else 0,
                ppi=supplier_result.ppi.ppi_score if supplier_result.ppi else 0,
                final_rank=rank,
                result_json=result_json,
                validation_warnings=warnings if warnings else None
            )

        # Update status to completed
        update_rfp_run_status(run_id, 'completed')

    except Exception as e:
        # Update status to failed
        update_rfp_run_status(run_id, 'failed')
        raise e

    return run_id


def _save_failed_result(run_id: int, supplier_result) -> None:
    """Save a failed supplier evaluation."""
    result_json = {
        'success': False,
        'error': supplier_result.error,
        'error_stage': supplier_result.error_stage,
        'processing_time_seconds': supplier_result.processing_time_seconds
    }

    save_supplier_result(
        rfp_run_id=run_id,
        supplier_name=supplier_result.supplier_name,
        submission_date='1970-01-01',  # Placeholder for failed
        experience_rating=0,
        absolute_score=0,
        ppi=0,
        final_rank=999,  # Failed results get low rank
        result_json=result_json,
        validation_warnings=[f"FAILED: {supplier_result.error}"]
    )


def _build_result_json(supplier_result, pipeline_result) -> Dict[str, Any]:
    """Build comprehensive result JSON for storage."""
    result = {
        'success': True,
        'processing_time_seconds': supplier_result.processing_time_seconds,
    }

    # Score breakdown
    if supplier_result.score:
        score = supplier_result.score
        result['score'] = {
            'total_weighted_score': score.total_weighted_score,
            'total_raw_score': score.total_raw_score,
            'total_max_score': score.total_max_score,
            'overall_percentage': score.overall_percentage,
            'criteria': [
                {
                    'criterion_id': cs.criterion_id,
                    'name': cs.name,
                    'raw_score': cs.raw_score,
                    'max_score': cs.max_score,
                    'weight': cs.weight,
                    'weighted_score': cs.weighted_score,
                    'percentage': cs.percentage,
                    'justification': cs.justification,
                    'evidence': cs.evidence
                }
                for cs in score.criteria_scores
            ],
            'risks': score.risks,
            'overall_summary': score.overall_summary
        }

    # PPI breakdown
    if supplier_result.ppi:
        ppi = supplier_result.ppi
        result['ppi'] = {
            'ppi_score': ppi.ppi_score,
            'ppi_grade': ppi.ppi_grade,
            'weighted_score': ppi.weighted_score,
            'consistency_score': ppi.consistency_score,
            'quality_score': ppi.quality_score,
            'risk_penalty': ppi.risk_penalty
        }

    # Gap analysis
    if supplier_result.gaps:
        gaps = supplier_result.gaps
        result['gaps'] = {
            'total_gap_count': gaps.total_gap_count,
            'max_potential_improvement': gaps.max_potential_improvement,
            'critical_gaps': [g.name for g in gaps.critical_gaps],
            'high_gaps': [g.name for g in gaps.high_gaps],
            'medium_gaps': [g.name for g in gaps.medium_gaps]
        }

    # Relative performance
    if supplier_result.relative:
        rel = supplier_result.relative
        result['relative'] = {
            'rank': rel.rank,
            'percentile': rel.percentile,
            'tier': rel.tier.value,
            'normalized_score': rel.normalized_score,
            'distance_from_leader': rel.distance_from_leader,
            'relative_strengths': rel.relative_strengths,
            'relative_weaknesses': rel.relative_weaknesses
        }

    # Benchmarks (from pipeline result)
    if pipeline_result.benchmarks:
        bench = pipeline_result.benchmarks
        result['benchmarks'] = {
            'best_total_score': bench.best_total_score,
            'worst_total_score': bench.worst_total_score,
            'average_total_score': bench.average_total_score,
            'supplier_count': bench.supplier_count
        }

    return result


def get_run_summary(rfp_run_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a summary of an RFP run with winner and key stats.

    Args:
        rfp_run_id: The ID of the run

    Returns:
        Dictionary with run summary, or None if not found
    """
    run = get_rfp_run(rfp_run_id)
    if not run:
        return None

    results = get_run_results(rfp_run_id)
    if not results:
        return {**run, 'supplier_count': 0, 'winner': None}

    # Get winner (rank 1)
    winner = None
    for r in results:
        if r['final_rank'] == 1:
            winner = {
                'name': r['supplier_name'],
                'score': r['absolute_score'],
                'ppi': r['ppi']
            }
            break

    # Calculate stats
    scores = [r['absolute_score'] for r in results if r['final_rank'] != 999]
    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        **run,
        'supplier_count': len(results),
        'successful_count': len([r for r in results if r['final_rank'] != 999]),
        'winner': winner,
        'average_score': round(avg_score, 2),
        'results': results
    }


def delete_run(rfp_run_id: int) -> bool:
    """
    Delete an RFP run and all its results.

    Args:
        rfp_run_id: The ID of the run to delete

    Returns:
        bool: True if deleted, False if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if run exists
    cursor.execute("SELECT rfp_run_id FROM rfp_runs WHERE rfp_run_id = ?", (rfp_run_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    # Delete supplier results first (foreign key)
    cursor.execute("DELETE FROM supplier_results WHERE rfp_run_id = ?", (rfp_run_id,))

    # Delete the run
    cursor.execute("DELETE FROM rfp_runs WHERE rfp_run_id = ?", (rfp_run_id,))

    conn.commit()
    conn.close()

    return True
