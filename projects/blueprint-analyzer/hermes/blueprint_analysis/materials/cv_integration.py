"""
Integration between Agent 3 (Claude Vision) → Agent 4 (Material Matching).

Flow: Extracted materials → Normalize against library → Return matched IDs
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..models import ExtractedMaterial
from .matching_service import MaterialMatcher, UnitConverter


logger = logging.getLogger(__name__)


@dataclass
class MatchingConfig:
    """Configuration for material matching."""
    min_confidence: float = 0.70  # Flag items below this
    fuzzy_threshold: float = 0.85  # Accept fuzzy matches above this
    fallback_category: str = "other"


class ClaudeVisionMaterialMatchingBridge:
    """
    Orchestrates data flow from Claude Vision → Material Matching.

    Takes extracted materials from Claude Vision and:
    1. Fuzzy matches against 847-item library
    2. Converts units to standard form
    3. Returns normalized materials with library IDs
    """

    def __init__(self, config: MatchingConfig = None):
        self.config = config or MatchingConfig()
        self.matcher = MaterialMatcher()
        self.converter = UnitConverter()

    async def process_extracted_materials(
        self,
        extracted: List[ExtractedMaterial],
        blueprint_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process extracted materials through matching pipeline.

        Args:
            extracted: List of ExtractedMaterial from Claude Vision
            blueprint_id: ID for logging/tracking

        Returns:
            List of matched materials with library IDs + normalized units

        Raises:
            ValueError: If input validation fails
        """
        if not extracted:
            logger.warning(f"No materials extracted for {blueprint_id}")
            return []

        logger.info(f"Processing {len(extracted)} materials for {blueprint_id}")

        matched_materials = []
        low_confidence_items = []

        for material in extracted:
            try:
                # Match material to library
                match_result = self._match_and_normalize(material, blueprint_id)

                if match_result:
                    matched_materials.append(match_result)

                    # Flag low-confidence matches
                    if match_result["match_confidence"] < self.config.min_confidence:
                        low_confidence_items.append({
                            "material": material.name,
                            "matched_id": match_result["material_id"],
                            "confidence": match_result["match_confidence"]
                        })

            except Exception as e:
                logger.error(f"Error matching material '{material.name}': {e}")
                # Continue with next material (graceful degradation)
                continue

        # Log summary
        logger.info(f"Matched {len(matched_materials)}/{len(extracted)} materials for {blueprint_id}")

        if low_confidence_items:
            logger.warning(f"Low confidence matches ({len(low_confidence_items)}): "
                          f"{[item['material'] for item in low_confidence_items]}")

        return matched_materials

    def _match_and_normalize(
        self,
        material: ExtractedMaterial,
        blueprint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Match single material and normalize units.

        Returns matched material dict or None if no good match found.
        """
        # Fuzzy match against library (tolerates typos)
        matches = self.matcher.find_materials(
            material.name,
            category=material.category,
            threshold=0.70  # Lower threshold for fuzzy matching
        )

        if not matches:
            logger.warning(f"No library match for '{material.name}' in category '{material.category}'")
            return None

        best_match = matches[0]  # Highest confidence match

        # Convert units to standard form
        try:
            standardized_quantity = self.converter.convert(
                material_id=best_match["id"],
                quantity=material.quantity,
                from_unit=material.unit,
                to_unit=best_match.get("standard_unit", material.unit)
            )
        except Exception as e:
            logger.warning(f"Unit conversion failed for '{material.name}': {e}")
            standardized_quantity = material.quantity

        return {
            "material_id": best_match["id"],
            "original_name": material.name,
            "matched_name": best_match.get("primary_name", best_match["id"]),
            "quantity": standardized_quantity,
            "original_quantity": material.quantity,
            "unit": best_match.get("standard_unit", material.unit),
            "original_unit": material.unit,
            "category": best_match.get("category", material.category),
            "match_confidence": best_match.get("confidence", 0.85),
            "specifications": material.specifications or {},
            "room_location": material.room_location,
            "extracted_confidence": material.confidence,
            "combined_confidence": (
                (material.confidence + best_match.get("confidence", 0.85)) / 2
            )
        }


class MaterialMatchingValidator:
    """Validates material matching results."""

    @staticmethod
    def validate_matched_materials(materials: List[Dict]) -> List[str]:
        """
        Validate matched materials meet schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        required_fields = [
            "material_id", "matched_name", "quantity", "unit", "category"
        ]

        for i, mat in enumerate(materials):
            for field in required_fields:
                if field not in mat:
                    errors.append(f"Material {i}: missing field '{field}'")

            if mat.get("quantity", 0) <= 0:
                errors.append(f"Material {i}: invalid quantity {mat.get('quantity')}")

            if not (0 <= mat.get("match_confidence", -1) <= 1):
                errors.append(f"Material {i}: confidence out of range")

            if not mat.get("material_id", "").startswith("lib_"):
                errors.append(f"Material {i}: invalid library ID format")

        return errors


if __name__ == "__main__":
    print("✓ Claude Vision → Material Matching integration module ready")
