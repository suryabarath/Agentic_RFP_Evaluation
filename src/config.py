"""
Configuration Module

Loads and validates configuration from environment variables.
Uses python-dotenv to load from .env file for local development.
Supports both OpenAI and Anthropic providers.
"""

import os
from dotenv import load_dotenv
from typing import Optional, Literal

# Load environment variables from .env file
# This looks for .env in the project root directory
load_dotenv()


# Supported providers
PROVIDERS = {
    "anthropic": {
        "name": "Anthropic",
        "models": [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "default_model": "claude-sonnet-4-20250514",
        "key_prefix": "sk-ant-",
        "env_key": "ANTHROPIC_API_KEY"
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "default_model": "gpt-4o-mini",
        "key_prefix": "sk-",
        "env_key": "OPENAI_API_KEY"
    }
}


class Config:
    """
    Application configuration loaded from environment variables.

    Usage:
        from src.config import config
        api_key = config.get_api_key()
    """

    def __init__(self):
        # Provider selection (anthropic or openai)
        self.PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic").lower()

        # API Keys for both providers
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

        # Model to use (optional, with default based on provider)
        default_model = PROVIDERS.get(self.PROVIDER, {}).get("default_model", "gpt-4o-mini")
        self.MODEL: str = os.getenv("LLM_MODEL", default_model)

        # Legacy support
        self.OPENAI_MODEL: str = self.MODEL

        # Maximum tokens for response
        self.MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))

        # Temperature (0.0 = deterministic, 1.0 = creative)
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))

        # Mock mode - use simulated responses instead of real API
        self.USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

    def get_api_key(self) -> str:
        """Get the API key for the current provider."""
        if self.PROVIDER == "anthropic":
            return self.ANTHROPIC_API_KEY
        return self.OPENAI_API_KEY

    def set_runtime_config(
        self,
        provider: str = None,
        model: str = None,
        api_key: str = None,
        use_mock: bool = None
    ):
        """
        Update configuration at runtime (from Streamlit session).

        Args:
            provider: 'anthropic' or 'openai'
            model: Model name
            api_key: API key for the provider
            use_mock: Whether to use mock mode
        """
        if provider is not None:
            self.PROVIDER = provider.lower()
        if model is not None:
            self.MODEL = model
            self.OPENAI_MODEL = model
        if api_key is not None:
            if self.PROVIDER == "anthropic":
                self.ANTHROPIC_API_KEY = api_key
            else:
                self.OPENAI_API_KEY = api_key
        if use_mock is not None:
            self.USE_MOCK_LLM = use_mock

    def validate(self) -> tuple:
        """
        Validate that required configuration is present.

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        api_key = self.get_api_key()
        provider_info = PROVIDERS.get(self.PROVIDER, {})

        if not api_key:
            return False, f"{provider_info.get('env_key', 'API_KEY')} is not set."

        if api_key == "your_api_key_here":
            return False, "API key is still the placeholder value."

        # Check key prefix for the provider
        expected_prefix = provider_info.get("key_prefix", "sk-")
        if not api_key.startswith(expected_prefix):
            return False, f"API key doesn't look valid for {provider_info.get('name', 'provider')}."

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
        provider_info = PROVIDERS.get(self.PROVIDER, {})

        return {
            "is_configured": is_valid or self.USE_MOCK_LLM,
            "error": error if not self.USE_MOCK_LLM else None,
            "provider": self.PROVIDER,
            "provider_name": provider_info.get("name", self.PROVIDER),
            "model": self.MODEL,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE,
            "api_key_set": bool(self.get_api_key()),
            "api_key_preview": self._mask_api_key(),
            "use_mock": self.USE_MOCK_LLM
        }

    def _mask_api_key(self) -> str:
        """Return masked version of API key for display."""
        api_key = self.get_api_key()
        if not api_key:
            return "(not set)"
        if api_key == "your_api_key_here":
            return "(placeholder)"
        # Show first 10 chars and last 4 chars
        if len(api_key) > 18:
            return f"{api_key[:10]}...{api_key[-4:]}"
        return "(invalid format)"


# Create a singleton instance
config = Config()


# For testing
if __name__ == "__main__":
    print("=== Configuration Status ===")
    print()

    status = config.get_status()

    print(f"Provider: {status['provider_name']}")
    print(f"API Key Set: {status['api_key_set']}")
    print(f"API Key Preview: {status['api_key_preview']}")
    print(f"Model: {status['model']}")
    print(f"Max Tokens: {status['max_tokens']}")
    print(f"Temperature: {status['temperature']}")
    print(f"Mock Mode: {status['use_mock']}")
    print()

    is_valid, error = config.validate()
    if is_valid:
        print("✓ Configuration is valid!")
    else:
        print(f"✗ Configuration error: {error}")
