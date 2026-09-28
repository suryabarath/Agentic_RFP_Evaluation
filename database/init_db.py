"""
Database Initialization Script

This script creates all necessary tables for the RFP Evaluation system.
Run this script once to set up the database.
"""

import sqlite3
import os
from datetime import datetime


def get_db_path():
    """Get the path to the database file."""
    # Database will be in the same directory as this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'rfp.db')


def create_tables():
    """Create all database tables."""

    db_path = get_db_path()
    print(f"Creating database at: {db_path}")

    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 1: evaluation_criteria
    # Stores the criteria used to evaluate suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_criteria (
            criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            weight REAL NOT NULL,
            max_score INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT weight_check CHECK (weight >= 0 AND weight <= 100),
            CONSTRAINT max_score_check CHECK (max_score > 0)
        )
    """)

    # Table 2: rfp_runs
    # Tracks each evaluation batch
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rfp_runs (
            rfp_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            CONSTRAINT status_check CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
        )
    """)

    # Table 3: supplier_results
    # Stores evaluation results for each supplier
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfp_run_id INTEGER NOT NULL,
            supplier_name TEXT NOT NULL,
            submission_date TEXT NOT NULL,
            experience_rating INTEGER NOT NULL,
            absolute_score REAL NOT NULL,
            ppi REAL NOT NULL,
            final_rank INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            validation_warnings TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs(rfp_run_id),
            CONSTRAINT experience_check CHECK (experience_rating >= 1 AND experience_rating <= 10),
            CONSTRAINT score_check CHECK (absolute_score >= 0 AND absolute_score <= 100),
            CONSTRAINT ppi_check CHECK (ppi >= 0),
            CONSTRAINT rank_check CHECK (final_rank > 0)
        )
    """)

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("✓ Table 'evaluation_criteria' created")
    print("✓ Table 'rfp_runs' created")
    print("✓ Table 'supplier_results' created")
    print("\nDatabase initialization complete!")


def verify_tables():
    """Verify that all tables were created successfully."""

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("\nVerification:")
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")

    conn.close()


def seed_evaluation_criteria():
    """
    Seed the database with the 5 initial evaluation criteria.

    The weights MUST total 100% as per project requirements.
    This function is safe to call multiple times - it only adds
    criteria if the table is empty.
    """

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if criteria already exist
    cursor.execute("SELECT COUNT(*) FROM evaluation_criteria")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"\n⚠ Criteria already exist ({count} found). Skipping seed.")
        conn.close()
        return

    # Define the 5 evaluation criteria
    # Format: (name, description, weight, max_score, is_active)
    criteria = [
        (
            "Technical Capability",
            "Architecture, integrations, scalability, technical fit",
            30,  # weight (30%)
            10,  # max_score
            1    # is_active (1 = True)
        ),
        (
            "Implementation Plan",
            "Timeline, milestones, staffing, risk plan",
            20,  # weight (20%)
            10,  # max_score
            1    # is_active
        ),
        (
            "Commercial Value",
            "Pricing clarity, total cost, assumptions",
            20,  # weight (20%)
            10,  # max_score
            1    # is_active
        ),
        (
            "Security & Compliance",
            "Controls, certifications, privacy, auditability",
            20,  # weight (20%)
            10,  # max_score
            1    # is_active
        ),
        (
            "Support & Experience",
            "Support model, similar projects, references",
            10,  # weight (10%)
            10,  # max_score
            1    # is_active
        ),
    ]

    # Verify weights total 100%
    total_weight = sum(c[2] for c in criteria)
    if total_weight != 100:
        print(f"✗ Error: Weights total {total_weight}%, but must be 100%")
        conn.close()
        return

    # Insert all criteria
    cursor.executemany("""
        INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, criteria)

    conn.commit()

    print("\n✓ Seeded 5 evaluation criteria:")
    print(f"  Total weight: {total_weight}%")

    # Display what was added
    cursor.execute("SELECT criterion_id, name, weight, max_score FROM evaluation_criteria")
    rows = cursor.fetchall()

    print("\n  ID | Criterion                  | Weight | Max Score")
    print("  " + "-" * 55)
    for row in rows:
        print(f"  {row[0]:2} | {row[1]:26} | {row[2]:5}% | {row[3]}")

    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("RFP EVALUATION SYSTEM - DATABASE INITIALIZATION")
    print("=" * 60)
    print()

    # Create all tables
    create_tables()

    # Verify creation
    verify_tables()

    # Seed the evaluation criteria
    seed_evaluation_criteria()

    print()
    print("=" * 60)
    print("Database setup complete! Ready for application development.")
    print("=" * 60)
