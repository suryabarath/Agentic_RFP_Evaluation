"""
LLM Evaluator Module

Handles communication with the OpenAI API for evaluating supplier proposals.
Includes mock mode for development without API credits.
"""

import json
import random
import hashlib
from openai import OpenAI
from typing import Optional, Dict, Any, List

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
        """Check if the evaluator is properly configured (or in mock mode)."""
        return self.config.USE_MOCK_LLM or self.config.is_configured()

    def is_mock_mode(self) -> bool:
        """Check if mock mode is enabled."""
        return self.config.USE_MOCK_LLM

    def get_status(self) -> dict:
        """Get the current status of the evaluator."""
        status = self.config.get_status()
        status['mode'] = 'MOCK' if self.is_mock_mode() else 'LIVE'
        return status

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
            raise ValueError("LLM is not configured. Please set OPENAI_API_KEY or enable USE_MOCK_LLM in .env file.")

        # Use mock mode if enabled
        if self.is_mock_mode():
            return self._mock_evaluate(proposal_text, criteria, supplier_name)

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

    def _mock_evaluate(
        self,
        proposal_text: str,
        criteria: list,
        supplier_name: str
    ) -> Dict[str, Any]:
        """
        Generate a mock evaluation response for testing.
        Uses the proposal text to generate somewhat consistent scores.

        Args:
            proposal_text: The extracted text from the supplier's PDF
            criteria: List of criteria from the database
            supplier_name: Name of the supplier

        Returns:
            dict: Mock evaluation response matching the expected schema
        """
        # Use hash of proposal text for consistent but varied scores
        text_hash = int(hashlib.md5(proposal_text.encode()).hexdigest()[:8], 16)
        random.seed(text_hash)

        # Generate scores for each criterion
        criteria_results = []
        for criterion in criteria:
            max_score = criterion['max_score']

            # Generate a score between 5 and max_score (mostly good scores)
            base_score = random.randint(5, max_score)

            # Adjust based on keyword matching (simple heuristic)
            keywords = criterion['description'].lower().split()
            matches = sum(1 for kw in keywords if kw in proposal_text.lower())
            bonus = min(2, matches // 2)  # Up to +2 for keyword matches
            score = min(max_score, base_score + bonus)

            # Generate mock justification
            justifications = [
                f"The proposal addresses {criterion['name'].lower()} with moderate detail.",
                f"Good coverage of {criterion['name'].lower()} requirements.",
                f"The supplier demonstrates understanding of {criterion['name'].lower()}.",
                f"Solid approach to {criterion['name'].lower()} with some areas for improvement.",
                f"Comprehensive treatment of {criterion['name'].lower()} aspects.",
            ]

            # Generate mock evidence
            evidences = [
                f"The proposal mentions relevant aspects of {criterion['description'].lower()[:50]}...",
                f"Section discussing {criterion['name'].lower()} provides adequate detail.",
                f"Documentation shows attention to {criterion['name'].lower()} requirements.",
                f"The supplier's approach to {criterion['name'].lower()} is documented.",
                f"Evidence of {criterion['name'].lower()} capabilities found in proposal.",
            ]

            criteria_results.append({
                "criterion_id": criterion['criterion_id'],
                "score": score,
                "max_score": max_score,
                "justification": random.choice(justifications),
                "evidence": random.choice(evidences)
            })

        # Generate mock risks based on proposal length
        possible_risks = [
            "Timeline may be aggressive for the scope described",
            "Some technical details could be more specific",
            "Experience with similar scale projects not fully demonstrated",
            "Cost breakdown could be more detailed",
            "Support model details are limited",
            "Integration approach needs more clarification",
            "Resource allocation seems tight for deliverables",
        ]

        # Select 1-3 risks
        num_risks = random.randint(1, 3)
        risks = random.sample(possible_risks, num_risks)

        # Generate overall summary
        summaries = [
            f"{supplier_name} presents a solid proposal with good technical approach. The solution addresses most requirements with adequate detail. Some areas could benefit from additional clarification.",
            f"The proposal from {supplier_name} demonstrates competent understanding of requirements. Implementation approach is reasonable with identified strengths in technical capability.",
            f"{supplier_name} offers a competitive proposal with balanced coverage across evaluation criteria. The team appears capable with relevant experience in similar projects.",
            f"Overall, {supplier_name}'s proposal is well-structured and addresses key requirements. Pricing appears reasonable and timeline is achievable with proper resource allocation.",
        ]

        return {
            "supplier_name": supplier_name,
            "criteria": criteria_results,
            "risks": risks,
            "overall_summary": random.choice(summaries)
        }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are an expert RFP (Request for Proposal) evaluator with years of experience evaluating vendor proposals for enterprise software projects.

Your job is to objectively evaluate supplier proposals against specific criteria.

CRITICAL RULES - YOU MUST FOLLOW THESE:

1. ONLY USE EVIDENCE FROM THE PROPOSAL
   - Never invent, assume, or hallucinate information
   - If information is not in the proposal, give a lower score and note "Not addressed in proposal"
   - Quote or specifically reference the proposal text as evidence

2. EVALUATE EVERY CRITERION
   - You must provide a score for ALL criteria provided
   - Do not skip any criterion
   - Each criterion must have: criterion_id, score, max_score, justification, evidence

3. SCORING RULES
   - Scores must be integers from 0 to the criterion's max_score
   - 0 = Not addressed at all
   - 1-3 = Poorly addressed or major gaps
   - 4-6 = Partially addressed with some gaps
   - 7-8 = Well addressed with minor gaps
   - 9-10 = Excellently addressed with comprehensive detail
   - NEVER give a score higher than max_score

4. IDENTIFY RISKS
   - Note any risks, concerns, or red flags in the proposal
   - Include timeline risks, cost risks, technical risks, experience gaps
   - If no risks found, return empty array []

5. OUTPUT FORMAT
   - Return ONLY valid JSON
   - No markdown code blocks
   - No explanatory text before or after the JSON
   - Follow the exact structure specified"""

    def _build_prompt(self, proposal_text: str, criteria: list, supplier_name: str) -> str:
        """Build the evaluation prompt."""

        # Format criteria for the prompt
        criteria_text = "\n".join([
            f"{i+1}. {c['name']} (ID: {c['criterion_id']}, Max Score: {c['max_score']})\n"
            f"   Evaluate: {c['description']}\n"
            f"   Weight: {c['weight']}%"
            for i, c in enumerate(criteria)
        ])

        prompt = f"""Evaluate the following supplier proposal against the criteria provided.

══════════════════════════════════════════════════════════════════
SUPPLIER: {supplier_name}
══════════════════════════════════════════════════════════════════

EVALUATION CRITERIA ({len(criteria)} total):
{criteria_text}

══════════════════════════════════════════════════════════════════
PROPOSAL CONTENT:
══════════════════════════════════════════════════════════════════
{proposal_text}
══════════════════════════════════════════════════════════════════

YOUR TASK:
Evaluate this proposal against ALL {len(criteria)} criteria above.

REQUIRED JSON OUTPUT FORMAT:
{{
    "supplier_name": "{supplier_name}",
    "criteria": [
        {{
            "criterion_id": 1,
            "score": 8,
            "max_score": 10,
            "justification": "The proposal demonstrates strong technical capability with...",
            "evidence": "Page 3 states: 'Our microservices architecture provides...'"
        }},
        {{
            "criterion_id": 2,
            "score": 7,
            "max_score": 10,
            "justification": "Implementation plan is detailed but timeline is aggressive...",
            "evidence": "The Gantt chart on page 8 shows a 6-month timeline..."
        }}
    ],
    "risks": [
        "Timeline appears aggressive given the project scope",
        "Limited experience with similar scale implementations"
    ],
    "overall_summary": "This proposal presents a solid technical approach with competitive pricing. The vendor demonstrates relevant experience but the proposed timeline may need adjustment to accommodate proper testing phases."
}}

REMINDERS:
- You MUST include all {len(criteria)} criteria
- Each score must be 0 to that criterion's max_score (not higher!)
- Justification and evidence must be specific, not generic
- Return ONLY the JSON object, nothing else
"""
        return prompt

    def get_prompt_preview(self, proposal_text: str, criteria: list, supplier_name: str) -> dict:
        """
        Get a preview of the prompts that will be sent to the LLM.
        Useful for debugging and understanding what the LLM sees.

        Args:
            proposal_text: The extracted text from the supplier's PDF
            criteria: List of criteria from the database
            supplier_name: Name of the supplier

        Returns:
            dict: Contains 'system_prompt' and 'user_prompt'
        """
        return {
            'system_prompt': self._get_system_prompt(),
            'user_prompt': self._build_prompt(proposal_text, criteria, supplier_name),
            'total_system_chars': len(self._get_system_prompt()),
            'total_user_chars': len(self._build_prompt(proposal_text, criteria, supplier_name))
        }

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
