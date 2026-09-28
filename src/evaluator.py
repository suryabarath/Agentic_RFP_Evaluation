"""
LLM Evaluator Module

Handles communication with the OpenAI API for evaluating supplier proposals.
"""

import json
from openai import OpenAI
from typing import Optional, Dict, Any

from src.config import config
from src.schemas import SupplierEvaluation


class LLMEvaluator:
    """
    Evaluates supplier proposals using OpenAI's API.

    Usage:
        evaluator = LLMEvaluator()
        if evaluator.is_ready():
            result = evaluator.evaluate(proposal_text, criteria, supplier_name)
    """

    def __init__(self):
        """Initialize the evaluator with configuration."""
        self.config = config
        self._client: Optional[OpenAI] = None

    def is_ready(self) -> bool:
        """Check if the evaluator is properly configured."""
        return self.config.is_configured()

    def get_status(self) -> dict:
        """Get the current status of the evaluator."""
        return self.config.get_status()

    def _get_client(self) -> OpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            if not self.is_ready():
                raise ValueError("LLM is not configured. Please set OPENAI_API_KEY in .env file.")
            self._client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        return self._client

    def evaluate(
        self,
        proposal_text: str,
        criteria: list,
        supplier_name: str
    ) -> Dict[str, Any]:
        """
        Evaluate a supplier proposal against the given criteria.

        Args:
            proposal_text: The extracted text from the supplier's PDF
            criteria: List of criteria from the database
            supplier_name: Name of the supplier

        Returns:
            dict: Raw response from the LLM (before Pydantic validation)

        Raises:
            ValueError: If LLM is not configured
            Exception: If API call fails
        """
        if not self.is_ready():
            raise ValueError("LLM is not configured. Please set OPENAI_API_KEY in .env file.")

        # Build the prompt
        prompt = self._build_prompt(proposal_text, criteria, supplier_name)

        # Call the API
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE,
            response_format={"type": "json_object"}  # Ensure JSON response
        )

        # Extract the response content
        response_text = response.choices[0].message.content

        # Parse JSON
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are an expert RFP (Request for Proposal) evaluator. Your job is to evaluate supplier proposals against specific criteria.

IMPORTANT RULES:
1. Only use information found in the proposal - never invent or assume information
2. Evaluate every criterion provided
3. Score each criterion from 0 to the specified max_score
4. Provide specific evidence from the proposal for each score
5. Be objective and consistent
6. Identify any risks mentioned or implied in the proposal
7. Return ONLY valid JSON in the exact format specified

Your response must be valid JSON only - no markdown, no explanation, just the JSON object."""

    def _build_prompt(self, proposal_text: str, criteria: list, supplier_name: str) -> str:
        """Build the evaluation prompt."""

        # Format criteria for the prompt
        criteria_text = "\n".join([
            f"{i+1}. {c['name']} (ID: {c['criterion_id']}, Max Score: {c['max_score']})\n"
            f"   Evaluate: {c['description']}\n"
            f"   Weight: {c['weight']}%"
            for i, c in enumerate(criteria)
        ])

        prompt = f"""Please evaluate the following supplier proposal.

SUPPLIER NAME: {supplier_name}

EVALUATION CRITERIA:
{criteria_text}

PROPOSAL TEXT:
---
{proposal_text}
---

Return your evaluation as a JSON object with this exact structure:
{{
    "supplier_name": "{supplier_name}",
    "criteria": [
        {{
            "criterion_id": <criterion ID from above>,
            "score": <your score from 0 to max_score>,
            "max_score": <max score for this criterion>,
            "justification": "<why you gave this score - be specific>",
            "evidence": "<quote or reference specific parts of the proposal>"
        }}
    ],
    "risks": [
        "<risk 1>",
        "<risk 2>"
    ],
    "overall_summary": "<overall assessment of the proposal - at least 2 sentences>"
}}

IMPORTANT:
- Include ALL {len(criteria)} criteria in your response
- Each score must be between 0 and that criterion's max_score
- Justification must explain your reasoning
- Evidence must reference the actual proposal content
- If no risks are found, use an empty array []
"""
        return prompt

    def test_connection(self) -> tuple:
        """
        Test the connection to the OpenAI API.

        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_ready():
            is_valid, error = self.config.validate()
            return False, error

        try:
            client = self._get_client()

            # Make a minimal API call to test
            response = client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[{"role": "user", "content": "Say 'OK' if you receive this."}],
                max_tokens=10
            )

            return True, f"Connected successfully! Model: {self.config.OPENAI_MODEL}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"


# Create a singleton instance
evaluator = LLMEvaluator()


# For testing
if __name__ == "__main__":
    print("=== LLM Evaluator Status ===")
    print()

    status = evaluator.get_status()

    print(f"API Key Set: {status['api_key_set']}")
    print(f"API Key Preview: {status['api_key_preview']}")
    print(f"Model: {status['model']}")
    print(f"Max Tokens: {status['max_tokens']}")
    print(f"Temperature: {status['temperature']}")
    print()

    if evaluator.is_ready():
        print("✓ Evaluator is ready!")
        print()
        print("Testing connection...")
        success, message = evaluator.test_connection()
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
    else:
        print("✗ Evaluator is not ready")
        print(f"  Error: {status['error']}")
        print()
        print("To configure:")
        print("  1. Get an API key from https://platform.openai.com/api-keys")
        print("  2. Open .env file in the project root")
        print("  3. Replace 'your_openai_api_key_here' with your actual key")
