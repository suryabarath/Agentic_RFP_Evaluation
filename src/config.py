"""
Configuration Module

Loads and validates configuration from environment variables.
Uses python-dotenv to load from .env file for local development.
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
# This looks for .env in the project root directory
load_dotenv()


class Config:
    """
    Application configuration loaded from environment variables.

    Usage:
        from src.config import config
        api_key = config.OPENAI_API_KEY
    """

    def __init__(self):
        # OpenAI API Key (required)
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

        # Model to use (optional, with default)
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Maximum tokens for response
        self.MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))

        # Temperature (0.0 = deterministic, 1.0 = creative)
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))

    def validate(self) -> tuple:
        """
        Validate that required configuration is present.

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not self.OPENAI_API_KEY:
            return False, "OPENAI_API_KEY is not set. Please add it to your .env file."

        if self.OPENAI_API_KEY == "your_openai_api_key_here":
            return False, "OPENAI_API_KEY is still the placeholder value. Please add your actual API key."

        if not self.OPENAI_API_KEY.startswith("sk-"):
            return False, "OPENAI_API_KEY doesn't look valid. It should start with 'sk-'."

        return True, None

    def is_configured(self) -> bool:
        """Check if the API is properly configured."""
        is_valid, _ = self.validate()
        return is_valid

    def get_status(self) -> dict:
        """
        Get configuration status for display.

        Returns:
            dict: Status information (without exposing the actual API key)
        """
        is_valid, error = self.validate()

        return {
            "is_configured": is_valid,
            "error": error,
            "model": self.OPENAI_MODEL,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE,
            "api_key_set": bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY != "your_openai_api_key_here"),
            "api_key_preview": self._mask_api_key()
        }

    def _mask_api_key(self) -> str:
        """Return masked version of API key for display."""
        if not self.OPENAI_API_KEY:
            return "(not set)"
        if self.OPENAI_API_KEY == "your_openai_api_key_here":
            return "(placeholder)"
        # Show first 7 chars (sk-xxx) and last 4 chars
        if len(self.OPENAI_API_KEY) > 15:
            return f"{self.OPENAI_API_KEY[:7]}...{self.OPENAI_API_KEY[-4:]}"
        return "(invalid format)"


# Create a singleton instance
config = Config()


# For testing
if __name__ == "__main__":
    print("=== Configuration Status ===")
    print()

    status = config.get_status()

    print(f"API Key Set: {status['api_key_set']}")
    print(f"API Key Preview: {status['api_key_preview']}")
    print(f"Model: {status['model']}")
    print(f"Max Tokens: {status['max_tokens']}")
    print(f"Temperature: {status['temperature']}")
    print()

    is_valid, error = config.validate()
    if is_valid:
        print("✓ Configuration is valid!")
    else:
        print(f"✗ Configuration error: {error}")
