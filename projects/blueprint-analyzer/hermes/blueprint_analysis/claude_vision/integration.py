"""
Integration between Agent 2 (Preprocessing) → Agent 3 (Claude Vision).

Flow: Preprocessed image + features → Claude Vision analysis → ExtractedMaterial list
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import anthropic

from ..models import ExtractedMaterial, PreprocessedBlueprint


logger = logging.getLogger(__name__)


@dataclass
class ClaudeVisionConfig:
    """Configuration for Claude Vision service."""
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 2048
    timeout_seconds: int = 60


class ClaudeVisionIntegration:
    """
    Integrates Claude Vision API for blueprint material extraction.

    Takes preprocessed blueprint (image + features) and extracts materials.
    """

    def __init__(self, config: ClaudeVisionConfig = None):
        self.config = config or ClaudeVisionConfig()
        self.client = anthropic.Anthropic(api_key=self.config.api_key)

        # Tier 1 refined prompt (from validation sprint)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the refined system prompt with Tier 1 improvements."""
        return """You are an expert construction cost estimator analyzing architectural blueprints.
Your task is to extract materials, quantities, and specifications from blueprint images.

RESPONSE FORMAT - Return ONLY valid JSON (no markdown, no explanation):
{
  "confidence": 0.85,
  "rooms": [
    {
      "name": "Kitchen",
      "wall_area_sqft": 240,
      "floor_area_sqft": 180,
      "detected_items": ["cabinets", "countertop"]
    }
  ],
  "materials": [
    {
      "name": "2x4 Stud - SPF - 8ft",
      "quantity": 42,
      "unit": "pieces",
      "category": "lumber",
      "confidence": 0.94,
      "specifications": {"grade": "2", "species": "SPF"}
    }
  ],
  "analysis_notes": ["Blueprint scale verified", "Electrical work noted"]
}

TIER 1 IMPROVEMENTS:
1. 3D ISOMETRIC HANDLING: For 3D/isometric views, isolate components carefully.
   Apply -0.05 confidence penalty for perspective distortion.
2. ELECTRICAL SYMBOLS: Reference these carefully:
   - Circle = outlet, Square = switch, 3-way = three-way switch
   - GFCI = ground fault, 240V = double-pole breaker
3. DEGRADED IMAGES: If blueprint is faded/low-res:
   - Apply -0.10 to -0.15 confidence penalty
   - Flag uncertainty in notes
   - Only extract legible specifications
4. CALCULATION TRANSPARENCY: Show your work for derived quantities.
   Example: "42 studs calculated from 16-inch on-center spacing for 240 sqft walls"

MATERIAL CATEGORIES (use exactly):
lumber, drywall, electrical, plumbing, flooring, roofing, paint, hardware, insulation, other

UNIT STANDARDIZATION:
pieces, linear_feet, square_feet, board_feet, lbs, gallons, sheets, bundles, spools, coils, boxes

CONFIDENCE SCORING:
- 1.0 = explicitly labeled on blueprint
- 0.9 = clearly visible, standard calculation
- 0.8 = reasonable assumption based on context
- 0.7 = ambiguous, multiple interpretations
- <0.7 = too uncertain, flag for review

OUTPUT RULES:
- Extract ONLY materials visible in blueprint
- Never hallucinate materials not shown
- Flag confidence <0.70 items separately
- Include calculation rationale for derived quantities
- Report wall area (sqft), room count, complexity level"""

    async def extract_materials(
        self,
        preprocessed: PreprocessedBlueprint,
        image_data: bytes,
        image_media_type: str = "image/png"
    ) -> List[ExtractedMaterial]:
        """
        Extract materials from preprocessed blueprint using Claude Vision.

        Args:
            preprocessed: PreprocessedBlueprint with image path + features
            image_data: Raw image bytes
            image_media_type: MIME type (image/png, image/jpeg, etc.)

        Returns:
            List of ExtractedMaterial objects

        Raises:
            anthropic.APIError: If Claude API call fails
        """
        logger.info(f"Extracting materials from blueprint {preprocessed.blueprint_id}")

        # Build user prompt with feature hints
        user_prompt = self._build_user_prompt(preprocessed)

        try:
            # Call Claude Vision API
            import base64
            image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_media_type,
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ],
                    }
                ],
            )

            # Parse response
            response_text = message.content[0].text
            materials = self._parse_claude_response(response_text, preprocessed.blueprint_id)

            logger.info(f"Extracted {len(materials)} materials from {preprocessed.blueprint_id}")

            return materials

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Material extraction error: {e}")
            raise

    def _build_user_prompt(self, preprocessed: PreprocessedBlueprint) -> str:
        """Build user prompt with feature hints from preprocessing."""
        hints = []

        if preprocessed.features.get("material_callout_regions"):
            hints.append(f"Detected {len(preprocessed.features['material_callout_regions'])} material callout regions")

        if preprocessed.features.get("dimension_annotations"):
            hints.append(f"Found {len(preprocessed.features['dimension_annotations'])} dimension annotations")

        if preprocessed.features.get("room_boundaries"):
            hints.append(f"Identified {len(preprocessed.features['room_boundaries'])} room boundaries")

        quality = preprocessed.image_quality_score
        quality_text = "excellent" if quality > 0.9 else "good" if quality > 0.8 else "fair"
        hints.append(f"Image quality: {quality_text} ({quality:.1%})")

        hints_text = "\n".join(f"  - {h}" for h in hints)

        return f"""Analyze this blueprint and extract materials.

Pre-analysis observations:
{hints_text}

Please extract all materials visible in the blueprint, providing:
1. Material name and specifications
2. Quantity and unit
3. Room location (if visible)
4. Confidence score (0.0-1.0)
5. Any assumptions made

Return as JSON matching the specified format."""

    def _parse_claude_response(self, response_text: str, blueprint_id: str) -> List[ExtractedMaterial]:
        """
        Parse Claude's JSON response into ExtractedMaterial objects.

        Handles various response formats (raw JSON, markdown, partial).
        """
        import json
        import re

        try:
            # Try direct JSON parsing first
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown
            json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from markdown for {blueprint_id}")
                    return []
            else:
                logger.warning(f"No valid JSON found in response for {blueprint_id}")
                return []

        materials = []

        for mat_data in data.get("materials", []):
            try:
                material = ExtractedMaterial(
                    id=f"{blueprint_id}_{len(materials)}",
                    name=mat_data.get("name", "Unknown"),
                    quantity=float(mat_data.get("quantity", 0)),
                    unit=mat_data.get("unit", "pieces"),
                    category=mat_data.get("category", "other"),
                    confidence=float(mat_data.get("confidence", 0.7)),
                    room_location=mat_data.get("room_location"),
                    specifications=mat_data.get("specifications", {}),
                    extracted_from="claude_vision"
                )

                # Flag low-confidence items
                if material.confidence < 0.70:
                    logger.warning(f"Low confidence material: {material.name} ({material.confidence:.1%})")

                materials.append(material)

            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping malformed material: {e}")
                continue

        return materials


class PreprocessingClaudeVisionBridge:
    """
    Orchestrates data flow from Preprocessing → Claude Vision.

    Handles: Enhanced image + features → Material extraction
    """

    def __init__(self, vision_config: ClaudeVisionConfig = None):
        self.vision = ClaudeVisionIntegration(vision_config)

    async def process_preprocessed_blueprint(
        self,
        preprocessed: PreprocessedBlueprint,
        image_path: Path
    ) -> List[ExtractedMaterial]:
        """
        Extract materials from preprocessed blueprint.

        Args:
            preprocessed: PreprocessedBlueprint object with image path + features
            image_path: Path to enhanced image file

        Returns:
            List of extracted materials
        """
        logger.info(f"Processing preprocessed blueprint {preprocessed.blueprint_id}")

        # Read image file
        if not image_path.exists():
            logger.error(f"Preprocessed image not found: {image_path}")
            return []

        try:
            image_data = image_path.read_bytes()

            # Determine media type from file extension
            media_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".pdf": "application/pdf",
                ".tiff": "image/tiff",
            }.get(image_path.suffix.lower(), "image/png")

            # Extract materials
            materials = await self.vision.extract_materials(
                preprocessed,
                image_data,
                media_type
            )

            logger.info(f"Extracted {len(materials)} materials from {preprocessed.blueprint_id}")

            return materials

        except Exception as e:
            logger.error(f"Error processing preprocessed blueprint: {e}")
            raise


if __name__ == "__main__":
    # Quick test
    print("✓ Claude Vision integration module ready")
    print(f"  - System prompt length: {len(ClaudeVisionIntegration()._build_system_prompt())} chars")
    print(f"  - Tier 1 improvements: 4 (3D, electrical, degraded, transparency)")
