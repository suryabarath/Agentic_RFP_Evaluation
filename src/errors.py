"""
Custom Exceptions for RFP Evaluation System

Defines specific exception types for different error scenarios,
enabling precise error handling and user-friendly error messages.
"""

from typing import Optional, Dict, Any


class RFPEvaluationError(Exception):
    """Base exception for all RFP evaluation errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize the error.

        Args:
            message: Human-readable error message
            details: Additional context about the error
            suggestion: Suggested action to resolve the error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion
        }


# ============================================================================
# PDF Processing Errors
# ============================================================================

class PDFExtractionError(RFPEvaluationError):
    """Error during PDF text extraction."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        suggestion = "Ensure the PDF is not corrupted and contains extractable text."
        super().__init__(message, details, suggestion)
        self.filename = filename


class PDFTooShortError(PDFExtractionError):
    """PDF content too short to be a valid proposal."""

    def __init__(self, filename: str, char_count: int, min_required: int = 100):
        message = f"PDF content too short ({char_count} chars, minimum {min_required} required)"
        details = {
            "filename": filename,
            "char_count": char_count,
            "min_required": min_required
        }
        suggestion = "The PDF may be image-based or scanned. Consider OCR processing."
        super().__init__(message, filename, details)
        self.suggestion = suggestion


class PDFCorruptedError(PDFExtractionError):
    """PDF file is corrupted or invalid."""

    def __init__(self, filename: str, original_error: str):
        message = f"PDF file is corrupted or invalid: {original_error}"
        details = {"filename": filename, "original_error": original_error}
        suggestion = "Try re-exporting the PDF from the source application."
        super().__init__(message, filename, details)
        self.suggestion = suggestion


# ============================================================================
# LLM/API Errors
# ============================================================================

class LLMError(RFPEvaluationError):
    """Error during LLM API interaction."""
    pass


class LLMRateLimitError(LLMError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        message = "API rate limit exceeded"
        details = {"retry_after_seconds": retry_after}
        suggestion = "Wait a moment and try again, or reduce the number of concurrent requests."
        super().__init__(message, details, suggestion)
        self.retry_after = retry_after


class LLMAuthenticationError(LLMError):
    """API authentication failed."""

    def __init__(self, details: Optional[str] = None):
        message = "API authentication failed"
        suggestion = "Check your OPENAI_API_KEY in the .env file."
        super().__init__(message, {"details": details}, suggestion)


class LLMResponseError(LLMError):
    """LLM returned an invalid or unexpected response."""

    def __init__(self, message: str, raw_response: Optional[Any] = None):
        details = {"raw_response_preview": str(raw_response)[:500] if raw_response else None}
        suggestion = "The LLM may be experiencing issues. Try again or switch to mock mode."
        super().__init__(message, details, suggestion)


# ============================================================================
# Validation Errors
# ============================================================================

class ValidationError(RFPEvaluationError):
    """Error during response validation."""
    pass


class MissingCriteriaError(ValidationError):
    """Required criteria missing from response."""

    def __init__(self, missing_criteria: list, supplier_name: str):
        message = f"Missing evaluation criteria: {', '.join(missing_criteria)}"
        details = {
            "supplier_name": supplier_name,
            "missing_criteria": missing_criteria
        }
        suggestion = "This may be a temporary LLM issue. Try evaluating again."
        super().__init__(message, details, suggestion)


class InvalidScoreError(ValidationError):
    """Score value is invalid or out of range."""

    def __init__(
        self,
        criterion_name: str,
        score: Any,
        max_score: int,
        supplier_name: str
    ):
        message = f"Invalid score {score} for '{criterion_name}' (max: {max_score})"
        details = {
            "criterion_name": criterion_name,
            "score_value": score,
            "max_score": max_score,
            "supplier_name": supplier_name
        }
        suggestion = "Score will be clamped to valid range during normalization."
        super().__init__(message, details, suggestion)


# ============================================================================
# Database Errors
# ============================================================================

class DatabaseError(RFPEvaluationError):
    """Error during database operations."""
    pass


class DatabaseNotFoundError(DatabaseError):
    """Database file not found."""

    def __init__(self, db_path: str):
        message = f"Database not found at {db_path}"
        details = {"db_path": db_path}
        suggestion = "Run 'python database/init_db.py' to initialize the database."
        super().__init__(message, details, suggestion)


class DatabaseLockedError(DatabaseError):
    """Database is locked by another process."""

    def __init__(self, db_path: str):
        message = "Database is locked by another process"
        details = {"db_path": db_path}
        suggestion = "Close other applications using the database and try again."
        super().__init__(message, details, suggestion)


# ============================================================================
# Pipeline Errors
# ============================================================================

class PipelineError(RFPEvaluationError):
    """Error during pipeline execution."""

    def __init__(
        self,
        message: str,
        stage: str,
        supplier_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        full_details = {"stage": stage, "supplier_name": supplier_name}
        if details:
            full_details.update(details)
        super().__init__(message, full_details)
        self.stage = stage
        self.supplier_name = supplier_name


class NoSuppliersError(PipelineError):
    """No suppliers provided for evaluation."""

    def __init__(self):
        message = "No suppliers provided for evaluation"
        super().__init__(message, stage="initialization")
        self.suggestion = "Upload at least one supplier PDF to evaluate."


class AllSuppliersFailedError(PipelineError):
    """All supplier evaluations failed."""

    def __init__(self, failure_count: int, errors: list):
        message = f"All {failure_count} supplier evaluations failed"
        details = {"failure_count": failure_count, "errors": errors[:5]}  # First 5 errors
        super().__init__(message, stage="evaluation", details=details)
        self.suggestion = "Check PDF files and try again. Consider using mock mode for testing."


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(RFPEvaluationError):
    """Error in application configuration."""
    pass


class MissingAPIKeyError(ConfigurationError):
    """API key not configured."""

    def __init__(self, key_name: str = "OPENAI_API_KEY"):
        message = f"Required API key not configured: {key_name}"
        details = {"key_name": key_name}
        suggestion = f"Set {key_name} in your .env file or use USE_MOCK_LLM=true for testing."
        super().__init__(message, details, suggestion)


class InvalidWeightsError(ConfigurationError):
    """Criteria weights don't sum to 100."""

    def __init__(self, total_weight: float):
        message = f"Criteria weights sum to {total_weight:.1f}%, expected 100%"
        details = {"total_weight": total_weight}
        suggestion = "Adjust weights in the database to sum to exactly 100%."
        super().__init__(message, details, suggestion)


# ============================================================================
# Utility Functions
# ============================================================================

def format_error_for_ui(error: Exception) -> Dict[str, Any]:
    """
    Format any exception for display in the UI.

    Args:
        error: The exception to format

    Returns:
        dict: Formatted error information
    """
    if isinstance(error, RFPEvaluationError):
        return error.to_dict()

    # Generic exception handling
    return {
        "error_type": error.__class__.__name__,
        "message": str(error),
        "details": {},
        "suggestion": "An unexpected error occurred. Please try again."
    }


def handle_api_error(error: Exception) -> LLMError:
    """
    Convert API exceptions to appropriate LLMError subclass.

    Args:
        error: The original API exception

    Returns:
        LLMError: Appropriate error subclass
    """
    error_str = str(error).lower()

    if "rate limit" in error_str or "429" in error_str:
        return LLMRateLimitError()
    elif "authentication" in error_str or "401" in error_str or "api key" in error_str:
        return LLMAuthenticationError(str(error))
    else:
        return LLMResponseError(str(error))


# For testing
if __name__ == "__main__":
    print("=== Testing Custom Exceptions ===")
    print()

    # Test PDF errors
    err = PDFTooShortError("test.pdf", 50)
    print(f"PDFTooShortError: {err.message}")
    print(f"  Suggestion: {err.suggestion}")
    print(f"  Dict: {err.to_dict()}")
    print()

    # Test validation errors
    err = MissingCriteriaError(["Security", "Pricing"], "TestCorp")
    print(f"MissingCriteriaError: {err.message}")
    print()

    # Test configuration errors
    err = MissingAPIKeyError()
    print(f"MissingAPIKeyError: {err.message}")
    print(f"  Suggestion: {err.suggestion}")
    print()

    print("All error classes working correctly!")
