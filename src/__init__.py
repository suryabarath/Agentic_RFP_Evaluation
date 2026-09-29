"""
RFP Evaluation System

A comprehensive system for evaluating RFP (Request for Proposal) supplier
submissions using LLM-powered analysis and deterministic scoring.

Main Components:
- orchestrator: Run the full evaluation pipeline
- evaluator: LLM-powered proposal evaluation
- scorer: Weighted score calculation
- ranking: Deterministic supplier ranking
- export: JSON export utilities
"""

__version__ = "1.0.0"

# Key exports for easy importing
from src.orchestrator import Orchestrator, SupplierInput, PipelineResult
from src.export import export_full_report, export_summary, to_json_string
