"""garage_ai diagnostic client - AI inference layer.

Phase 4: Structured parsing of diagnosis responses with confidence scoring.
"""

import subprocess
import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GarageAIClient:
    """Client for garage_ai inference with structured diagnosis parsing."""

    # Severity keywords with confidence weights
    SEVERITY_KEYWORDS = {
        "critical": {
            "keywords": ["critical", "severe", "catastrophic", "immediately", "do not drive"],
            "level": "critical",
            "confidence_boost": 0.3
        },
        "high": {
            "keywords": ["high", "serious", "urgent", "requires soon", "failing"],
            "level": "high",
            "confidence_boost": 0.2
        },
        "medium": {
            "keywords": ["moderate", "medium", "should check", "likely", "probable"],
            "level": "medium",
            "confidence_boost": 0.1
        },
        "low": {
            "keywords": ["low", "minor", "check", "may be", "possibly"],
            "level": "low",
            "confidence_boost": 0.05
        }
    }

    # Complexity keywords
    COMPLEXITY_KEYWORDS = {
        "simple": ["simple", "easy", "quick", "replace part", "sensor replacement", "fluid top"],
        "moderate": ["moderate", "medium difficulty", "inspect", "test", "adjustment", "wire"],
        "complex": ["complex", "complicated", "involved", "major repair", "engine work", "transmission", "overhaul"]
    }

    # Confidence markers
    CONFIDENCE_KEYWORDS = {
        "explicit": ["definitely", "clearly", "obviously", "without doubt", "certain"],
        "probable": ["likely", "probably", "suggests", "indicates", "typical of"],
        "speculative": ["may", "might", "could", "possibly", "perhaps"]
    }

    def __init__(self, garage_ai_home: Optional[str] = None):
        self.garage_ai_home = garage_ai_home or "/home/tp/projects/active/garage_ai"

    def diagnose(
        self,
        diagnostic_prompt: str,
        timeout: int = 30
    ) -> Optional[str]:
        """Run diagnostic inference via garage_ai.

        Returns: Diagnosis text or None if error
        """
        try:
            cmd = [
                "bash",
                f"{self.garage_ai_home}/garage_tool.sh",
                diagnostic_prompt
            ]

            logger.info(f"Running garage_ai...")
            logger.debug(f"Prompt: {diagnostic_prompt[:100]}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"garage_ai error: {result.stderr}")
                return None

            logger.info("Diagnosis complete")
            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Failed: {e}")
            return None

    def _extract_likely_causes(self, diagnosis_text: str) -> Tuple[List[str], float]:
        """Extract likely causes from diagnosis text.

        Returns: (causes list, cause_extraction_confidence)
        """
        causes = []
        confidence = 0.0

        # Look for explicit cause sections
        cause_patterns = [
            r"(?:likely|probable|possible|root).*?causes?:?\s*\n(.*?)(?:\n\n|\d\.|$)",
            r"(?:possible causes?)[:\s]+(.+?)(?:\n\n|$)",
            r"(?:most likely).*?:?\s*(.+?)(?:\n|$)",
        ]

        found_explicit_cause = False
        for pattern in cause_patterns:
            matches = re.finditer(pattern, diagnosis_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                cause_text = match.group(1)
                # Split by bullet points, dashes, or numbers
                items = re.split(r'[•\-\*]\s+|\d+\)\s+|\n\s+', cause_text)
                for item in items:
                    item = item.strip()
                    if item and len(item) > 5:
                        causes.append(item)
                        found_explicit_cause = True

        # If no structured causes found, look for cause keywords in sentences
        if not causes:
            sentences = re.split(r'[.!?]\s+', diagnosis_text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in ["cause", "caused by", "result of", "due to"]):
                    sentence = sentence.strip()
                    if len(sentence) > 10:
                        causes.append(sentence)

        # Calculate confidence based on extraction quality
        if found_explicit_cause:
            confidence = 0.25  # Found explicit causes section
        elif causes:
            confidence = 0.15  # Found cause-related keywords
        else:
            confidence = 0.0

        return causes[:5], confidence  # Return top 5 causes

    def _extract_severity(self, diagnosis_text: str) -> Tuple[str, float]:
        """Extract severity level from diagnosis text.

        Returns: (severity_level, severity_confidence)
        """
        text_lower = diagnosis_text.lower()
        max_severity = "low"
        max_score = 0.0

        for severity_key, severity_config in self.SEVERITY_KEYWORDS.items():
            for keyword in severity_config["keywords"]:
                if keyword in text_lower:
                    # Count occurrences
                    count = text_lower.count(keyword)
                    score = count * 0.1 + severity_config["confidence_boost"]

                    if score > max_score:
                        max_score = score
                        max_severity = severity_config["level"]

        # Clamp confidence to 0-0.3 for severity
        severity_confidence = min(max_score, 0.3)

        return max_severity, severity_confidence

    def _extract_next_steps(self, diagnosis_text: str) -> Tuple[List[str], float]:
        """Extract next diagnostic steps from diagnosis text.

        Returns: (steps list, steps_confidence)
        """
        steps = []
        confidence = 0.0

        # Look for explicit steps sections
        steps_patterns = [
            r"(?:next|diagnostic|recommended).*?steps?:?\s*\n(.*?)(?:\n\n|$)",
            r"(?:do the following|check the following):?\s*\n(.*?)(?:\n\n|$)",
            r"(?:procedure|process):?\s*\n(.*?)(?:\n\n|$)",
        ]

        found_explicit_steps = False
        for pattern in steps_patterns:
            matches = re.finditer(pattern, diagnosis_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                steps_text = match.group(1)
                # Split by numbered items, bullets, or lines
                items = re.split(r'\n\s*(?:\d+[.)]\s+|[•\-\*]\s+)', steps_text)
                for item in items:
                    item = item.strip()
                    if item and len(item) > 5:
                        steps.append(item)
                        found_explicit_steps = True

        # If no structured steps, look for action keywords
        if not steps:
            sentences = re.split(r'[.!?]\s+', diagnosis_text)
            action_keywords = ["check", "inspect", "test", "verify", "measure", "replace", "diagnose", "scan"]
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in action_keywords):
                    sentence = sentence.strip()
                    if len(sentence) > 10:
                        steps.append(sentence)

        # Calculate confidence
        if found_explicit_steps:
            confidence = 0.25  # Found explicit steps section
        elif steps:
            confidence = 0.15  # Found action-related keywords
        else:
            confidence = 0.0

        return steps[:8], confidence  # Return top 8 steps

    def _extract_repair_complexity(self, diagnosis_text: str) -> Tuple[str, float]:
        """Extract repair complexity level from diagnosis text.

        Returns: (complexity, complexity_confidence)
        """
        text_lower = diagnosis_text.lower()

        # Count keyword matches
        complexity_scores = {
            "simple": 0.0,
            "moderate": 0.0,
            "complex": 0.0
        }

        for complexity_level, keywords in self.COMPLEXITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    complexity_scores[complexity_level] += 1

        # Determine complexity based on scores
        max_complexity = "moderate"  # Default
        max_score = complexity_scores["moderate"]

        for level, score in complexity_scores.items():
            if score > max_score:
                max_score = score
                max_complexity = level

        # Confidence based on keyword matches
        total_matches = sum(complexity_scores.values())
        complexity_confidence = min(total_matches * 0.08, 0.25)

        return max_complexity, complexity_confidence

    def _calculate_confidence_score(
        self,
        diagnosis_text: str,
        causes_confidence: float,
        severity_confidence: float,
        steps_confidence: float,
        complexity_confidence: float
    ) -> float:
        """Calculate overall confidence score (0-1).

        High confidence: explicit keywords + multiple sources of evidence
        Medium: probable causes with reasoning
        Low: speculative or single evidence
        """
        # Base score from component confidences
        component_score = (causes_confidence + severity_confidence + steps_confidence + complexity_confidence) / 4

        # Check for confidence markers
        explicit_count = sum(1 for kw in self.CONFIDENCE_KEYWORDS["explicit"] if kw in diagnosis_text.lower())
        probable_count = sum(1 for kw in self.CONFIDENCE_KEYWORDS["probable"] if kw in diagnosis_text.lower())
        speculative_count = sum(1 for kw in self.CONFIDENCE_KEYWORDS["speculative"] if kw in diagnosis_text.lower())

        # Adjust based on confidence markers
        if explicit_count > 2:
            component_score += 0.25
        elif probable_count > 2:
            component_score += 0.15
        elif speculative_count > 2:
            component_score -= 0.1

        # Adjust based on text length and detail
        word_count = len(diagnosis_text.split())
        if word_count > 100:
            component_score += 0.1
        elif word_count < 20:
            component_score -= 0.1

        # Adjust based on structured content
        if "\n" in diagnosis_text:
            component_score += 0.05

        # Clamp to 0-1
        return max(0.0, min(1.0, component_score))

    def parse_diagnosis(self, diagnosis_text: str) -> Dict[str, Any]:
        """Parse diagnosis output into structured format.

        Returns dict with keys:
        - likely_causes: List[str]
        - severity: str (critical/high/medium/low)
        - next_steps: List[str]
        - repair_complexity: str (simple/moderate/complex)
        - confidence: float (0-1)
        - raw: str (original text)
        """
        if not diagnosis_text or not diagnosis_text.strip():
            logger.warning("Empty diagnosis text")
            return {
                "likely_causes": [],
                "severity": "unknown",
                "next_steps": [],
                "repair_complexity": "unknown",
                "confidence": 0.0,
                "raw": diagnosis_text or ""
            }

        # Extract all components
        likely_causes, causes_conf = self._extract_likely_causes(diagnosis_text)
        severity, severity_conf = self._extract_severity(diagnosis_text)
        next_steps, steps_conf = self._extract_next_steps(diagnosis_text)
        repair_complexity, complexity_conf = self._extract_repair_complexity(diagnosis_text)

        # Calculate overall confidence
        overall_confidence = self._calculate_confidence_score(
            diagnosis_text,
            causes_conf,
            severity_conf,
            steps_conf,
            complexity_conf
        )

        logger.info(f"Parsed diagnosis - Severity: {severity}, Confidence: {overall_confidence:.2f}")

        return {
            "likely_causes": likely_causes,
            "severity": severity,
            "next_steps": next_steps,
            "repair_complexity": repair_complexity,
            "confidence": overall_confidence,
            "raw": diagnosis_text
        }

    def format_report(
        self,
        diagnostic_data: Dict[str, Any],
        diagnosis: Dict[str, Any]
    ) -> str:
        """Format comprehensive diagnostic report with structured analysis.

        Includes:
        - Structured causes with bullet points
        - Severity badge/indicator
        - Step-by-step diagnostic path
        - Confidence percentage
        """
        # Extract fields with defaults
        likely_causes = diagnosis.get('likely_causes', [])
        severity = diagnosis.get('severity', 'unknown')
        next_steps = diagnosis.get('next_steps', [])
        repair_complexity = diagnosis.get('repair_complexity', 'unknown')
        confidence = diagnosis.get('confidence', 0.0)

        # Format severity badge
        severity_symbols = {
            'critical': '!',
            'high': 'H',
            'medium': 'M',
            'low': 'L'
        }
        severity_symbol = severity_symbols.get(severity, '?')

        # Format complexity badge
        complexity_symbols = {
            'simple': 'S',
            'moderate': 'M',
            'complex': 'C'
        }
        complexity_symbol = complexity_symbols.get(repair_complexity, '?')

        # Format causes section
        causes_section = ""
        if likely_causes:
            causes_section = "Likely Causes:\n"
            for i, cause in enumerate(likely_causes, 1):
                causes_section += f"  {i}. {cause}\n"
        else:
            causes_section = "Likely Causes: Unable to determine from diagnosis\n"

        # Format steps section
        steps_section = ""
        if next_steps:
            steps_section = "\nDiagnostic Steps:\n"
            for i, step in enumerate(next_steps, 1):
                steps_section += f"  {i}. {step}\n"
        else:
            steps_section = "\nDiagnostic Steps: See raw diagnosis for recommendations\n"

        # Get vehicle info
        vehicle = diagnostic_data.get('vehicle', {})
        dtcs = diagnostic_data.get('dtcs', {})
        live_data = diagnostic_data.get('live_data', {})

        # Format live data
        live_data_str = ""
        if live_data:
            live_data_str = "\n".join(f"  {k}: {v:.2f}" for k, v in live_data.items())
        else:
            live_data_str = "  No data"

        # Build complete report
        report = f"""═══════════════════════════════════════════════════════════════════
              VEHICLE DIAGNOSTIC REPORT - PHASE 4
Generated: {datetime.utcnow().isoformat()}

Vehicle: {vehicle.get('year', 'Unknown')} {vehicle.get('make', 'Unknown')} {vehicle.get('model', 'Unknown')}
VIN: {vehicle.get('vin', 'Unknown')}

Active DTCs: {', '.join(dtcs.get('active', [])) or 'None'}
Pending DTCs: {', '.join(dtcs.get('pending', [])) or 'None'}

Live Data:
{live_data_str}

═══════════════════════════════════════════════════════════════════
ANALYSIS RESULTS:

Severity: [{severity_symbol}] {severity.upper()}
Repair Complexity: [{complexity_symbol}] {repair_complexity.upper()}
Analysis Confidence: {confidence * 100:.1f}%

{causes_section}{steps_section}

═══════════════════════════════════════════════════════════════════
DETAILED DIAGNOSIS:

{diagnosis.get('raw', 'No diagnosis available')}

═══════════════════════════════════════════════════════════════════
"""

        return report


def diagnose_vehicle(
    diagnostic_data: Dict[str, Any],
    vehicle_make: str = "Unknown",
    vehicle_model: str = "Unknown",
    vehicle_year: int = 2020
) -> Tuple[Optional[str], Dict[str, Any]]:
    """End-to-end diagnosis with structured parsing.

    Returns: (formatted_report, parsed_diagnosis_dict)
    """
    from formatters import format_diagnostic_prompt

    client = GarageAIClient()

    prompt, structured = format_diagnostic_prompt(
        diagnostic_data,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        vehicle_year=vehicle_year
    )

    diagnosis_text = client.diagnose(prompt)
    if not diagnosis_text:
        logger.error("No diagnosis returned")
        return None, {}

    parsed = client.parse_diagnosis(diagnosis_text)
    report = client.format_report(structured, parsed)

    return report, parsed
