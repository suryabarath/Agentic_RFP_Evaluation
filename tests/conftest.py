"""
Pytest Configuration

Provides fixtures and configuration for the test suite.
"""

import pytest
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def sample_criteria():
    """Provide sample evaluation criteria for tests."""
    return [
        {"criterion_id": 1, "name": "Technical", "weight": 30.0, "max_score": 10},
        {"criterion_id": 2, "name": "Commercial", "weight": 20.0, "max_score": 10},
        {"criterion_id": 3, "name": "Security", "weight": 20.0, "max_score": 10},
        {"criterion_id": 4, "name": "Implementation", "weight": 20.0, "max_score": 10},
        {"criterion_id": 5, "name": "Support", "weight": 10.0, "max_score": 10},
    ]


@pytest.fixture
def criteria_lookup(sample_criteria):
    """Provide criteria lookup dict for tests."""
    return {c["criterion_id"]: c for c in sample_criteria}
