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


if __name__ == "__main__":
    print("=" * 60)
    print("RFP EVALUATION SYSTEM - DATABASE INITIALIZATION")
    print("=" * 60)
    print()

    # Create all tables
    create_tables()

    # Verify creation
    verify_tables()

    print()
    print("=" * 60)
    print("Next step: Run this script to seed the evaluation criteria")
    print("=" * 60)
