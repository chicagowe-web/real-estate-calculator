"""Inference client for garage-core GPU via Ollama.

All agents use this client for local inference instead of API calls.
Reduces token usage by 99% by routing synthesis/analysis to garage-core GPU.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("garage_core_inference")


class GarageCoreInference:
    """Client for Ollama inference on garage-core GPU."""

    def __init__(
        self,
        ollama_url: str = "http://192.168.0.129:11434",
        timeout_seconds: int = 30,
    ):
        self.ollama_url = ollama_url
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session: Optional[aiohttp.ClientSession] = None

        # Model selection by task
        self.models = {
            "fast": "gemma4:e4b",           # Fast, general purpose
            "reasoning": "gemma4:26b",      # Slower, better thinking
            "automotive": "garage-ai-v12:latest",  # Specialized
        }

        # Model parameters
        self.params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
        }

    async def connect(self) -> bool:
        """Connect to Ollama server.

        Returns:
            True if successful
        """
        try:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

            # Test connection
            async with self.session.get(f"{self.ollama_url}/api/tags") as resp:
                if resp.status == 200:
                    logger.info(f"Connected to Ollama at {self.ollama_url}")
                    return True
                else:
                    logger.error(f"Ollama returned status {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection."""
        if self.session:
            await self.session.close()

    async def generate(
        self,
        prompt: str,
        model_type: str = "fast",
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> str:
        """Generate text using Ollama.

        Args:
            prompt: Input prompt
            model_type: Model to use (fast, reasoning, automotive)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response

        Returns:
            Generated text
        """
        if not self.session:
            logger.error("Not connected to Ollama")
            return ""

        model = self.models.get(model_type, self.models["fast"])

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "num_predict": max_tokens,
                **self.params,
            }

            async with self.session.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    if stream:
                        # Streaming response
                        result = ""
                        async for line in resp.content:
                            data = json.loads(line)
                            result += data.get("response", "")
                        return result
                    else:
                        # Full response
                        data = await resp.json()
                        return data.get("response", "")
                else:
                    logger.error(f"Ollama error: {resp.status}")
                    return ""

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ""

    async def summarize_research(self, findings: str) -> str:
        """Summarize research findings.

        Args:
            findings: Raw research findings

        Returns:
            Synthesized summary
        """
        prompt = f"""Synthesize these research findings into a concise report:

{findings}

Generate a structured response with:
1. Overview (2-3 sentences)
2. Best Practices (3-5 bullets)
3. Common Pitfalls (2-3 bullets)
4. Pro Tips (2-3 bullets)

Keep it concise and actionable."""

        return await self.generate(
            prompt,
            model_type="reasoning",  # Use better model for synthesis
            max_tokens=800,
        )

    async def explain_anomaly(
        self,
        device: str,
        metric: str,
        current_value: float,
        expected_value: float,
        stddev: float,
    ) -> str:
        """Explain an infrastructure anomaly.

        Args:
            device: Device name
            metric: Metric name
            current_value: Current value
            expected_value: Expected value
            stddev: Standard deviation

        Returns:
            Explanation
        """
        prompt = f"""Explain this infrastructure anomaly:

Device: {device}
Metric: {metric}
Current value: {current_value:.1f}
Expected value: {expected_value:.1f}
Standard deviations away: {abs(current_value - expected_value) / stddev:.1f}

Provide:
1. Brief explanation (1-2 sentences)
2. Likely cause (1-2 bullets)
3. Severity assessment (critical/high/medium/low)
4. Suggested fix via Hermes (1 command)"""

        return await self.generate(
            prompt,
            model_type="fast",
            max_tokens=300,
        )

    async def assess_update_risk(self, update_description: str) -> str:
        """Assess risk of a system update.

        Args:
            update_description: Description of the update

        Returns:
            Risk assessment
        """
        prompt = f"""Assess the risk of this system update:

{update_description}

Provide:
1. Risk level (critical/high/medium/low)
2. Potential issues (2-3 bullets)
3. Rollback plan (1-2 bullets)
4. Recommendation (proceed/wait/manual review)"""

        return await self.generate(
            prompt,
            model_type="fast",
            max_tokens=400,
        )

    async def suggest_remediation(self, alert_description: str) -> str:
        """Suggest remediation for an alert.

        Args:
            alert_description: Description of the alert

        Returns:
            Suggested Hermes command
        """
        prompt = f"""Given this infrastructure alert, suggest a Hermes command to fix it:

{alert_description}

Respond ONLY with a single Hermes command in this format:
hermes ask "describe your intent here"

Make it specific, actionable, and focused on the root cause."""

        response = await self.generate(
            prompt,
            model_type="fast",
            max_tokens=100,
        )

        # Extract command
        if "hermes ask" in response:
            return response.strip()
        return f'hermes ask "investigate: {alert_description[:50]}"'

    async def extract_key_points(self, text: str) -> list[str]:
        """Extract key points from text.

        Args:
            text: Input text

        Returns:
            List of key points
        """
        prompt = f"""Extract the 5 most important key points from this text:

{text}

Format as a JSON array of strings:
["point 1", "point 2", "point 3", "point 4", "point 5"]

Respond ONLY with the JSON array."""

        response = await self.generate(
            prompt,
            model_type="fast",
            max_tokens=200,
        )

        try:
            return json.loads(response)
        except:
            return []

    async def classify_alert(self, alert_title: str, description: str) -> dict:
        """Classify alert severity and type.

        Args:
            alert_title: Alert title
            description: Alert description

        Returns:
            Classification dict
        """
        prompt = f"""Classify this alert:

Title: {alert_title}
Description: {description}

Respond with a JSON object:
{{
  "severity": "critical|high|medium|low",
  "type": "threshold|anomaly|trend|service",
  "category": "cpu|memory|disk|network|service|application",
  "auto_remediate": true|false
}}

Respond ONLY with the JSON."""

        response = await self.generate(
            prompt,
            model_type="fast",
            max_tokens=150,
        )

        try:
            return json.loads(response)
        except:
            return {
                "severity": "medium",
                "type": "threshold",
                "category": "system",
                "auto_remediate": False,
            }

    async def health_check(self) -> bool:
        """Check if Ollama is healthy.

        Returns:
            True if healthy
        """
        try:
            async with self.session.get(f"{self.ollama_url}/api/tags") as resp:
                return resp.status == 200
        except:
            return False


# Global inference client (shared across all agents)
_inference_client: Optional[GarageCoreInference] = None


async def get_inference_client() -> GarageCoreInference:
    """Get or create global inference client.

    Returns:
        GarageCoreInference instance
    """
    global _inference_client

    if _inference_client is None:
        _inference_client = GarageCoreInference()
        await _inference_client.connect()

    return _inference_client


async def shutdown_inference() -> None:
    """Shutdown inference client."""
    global _inference_client

    if _inference_client:
        await _inference_client.disconnect()
        _inference_client = None
