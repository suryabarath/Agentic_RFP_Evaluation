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
    conn = sqlite3.connect(db_path)
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
