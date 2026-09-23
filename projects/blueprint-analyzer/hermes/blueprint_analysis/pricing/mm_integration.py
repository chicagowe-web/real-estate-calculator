"""
Integration between Agent 4 (Material Matching) → Agent 5 (Pricing).

Flow: Matched materials → Price lookup → Return pricing results
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from .service import PricingService, PricingConfig


logger = logging.getLogger(__name__)


@dataclass
class PricingIntegrationConfig:
    """Configuration for pricing integration."""
    region: str = "midwest"
    pricing_config: PricingConfig = None


class MaterialMatchingPricingBridge:
    """
    Orchestrates data flow from Material Matching → Pricing.

    Takes matched materials and:
    1. Looks up prices from multi-source (Home Depot, Lowe's, EstimationPro, CSV)
    2. Applies regional multipliers
    3. Returns pricing results with supplier info
    """

    def __init__(self, config: PricingIntegrationConfig = None):
        self.config = config or PricingIntegrationConfig()
        self.pricing_service = PricingService(self.config.pricing_config)

    async def process_matched_materials(
        self,
        matched_materials: List[Dict[str, Any]],
        estimate_id: str,
        region: str = None
    ) -> List[Dict[str, Any]]:
        """
        Look up prices for matched materials.

        Args:
            matched_materials: Output from Material Matching service
            estimate_id: ID for logging/tracking
            region: Optional region override (uses config default otherwise)

        Returns:
            List of pricing results with supplier info

        Raises:
            ValueError: If input validation fails
        """
        if not matched_materials:
            logger.warning(f"No matched materials for pricing lookup {estimate_id}")
            return []

        region = region or self.config.region
        logger.info(f"Looking up prices for {len(matched_materials)} materials ({region})")

        pricing_results = []
        failed_lookups = []

        for material in matched_materials:
            try:
                # Look up price for this material
                price_result = await self._lookup_and_price(material, region, estimate_id)

                if price_result:
                    pricing_results.append(price_result)
                else:
                    failed_lookups.append(material["matched_name"])

            except Exception as e:
                logger.error(f"Pricing lookup failed for '{material.get('matched_name')}': {e}")
                failed_lookups.append(material["matched_name"])
                # Continue with next material (graceful degradation)
                continue

        # Log summary
        logger.info(f"Priced {len(pricing_results)}/{len(matched_materials)} materials for {estimate_id}")
        if failed_lookups:
            logger.warning(f"Failed pricing lookups ({len(failed_lookups)}): {failed_lookups}")

        return pricing_results

    async def _lookup_and_price(
        self,
        material: Dict[str, Any],
        region: str,
        estimate_id: str
    ) -> Dict[str, Any]:
        """
        Look up price for single matched material.

        Returns pricing result dict with supplier, price, total cost.
        """
        material_id = material.get("material_id")
        material_name = material.get("matched_name", "Unknown")
        quantity = material.get("quantity", 0)
        unit = material.get("unit", "pieces")

        if quantity <= 0:
            logger.warning(f"Invalid quantity for {material_name}: {quantity}")
            return None

        # Look up price from pricing service
        try:
            price_info = await self.pricing_service.lookup_price(
                material_id=material_id,
                material_name=material_name,
                region=region
            )

            if not price_info:
                logger.warning(f"No price found for {material_name} in {region}")
                return None

            # Calculate total cost
            unit_price = price_info.get("unit_price", 0)
            total_price = unit_price * quantity

            # Apply regional multiplier if not already included
            regional_multiplier = self._get_regional_multiplier(region)
            if not price_info.get("regional_adjusted", False):
                total_price *= regional_multiplier

            return {
                "material_id": material_id,
                "matched_material_id": material_id,
                "product_name": price_info.get("product_name", material_name),
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "total_price": total_price,
                "source": price_info.get("source", "fallback"),
                "confidence": price_info.get("confidence", 0.80),
                "region": region,
                "regional_multiplier": regional_multiplier,
                "supplier": price_info.get("supplier", "unknown"),
                "category": material.get("category", "other"),
                "alternatives": price_info.get("alternatives", [])
            }

        except Exception as e:
            logger.error(f"Price lookup error for {material_name}: {e}")
            return None

    @staticmethod
    def _get_regional_multiplier(region: str) -> float:
        """Get regional price multiplier."""
        multipliers = {
            "ca": 1.30,        # California (high cost)
            "ny": 1.25,        # New York (high cost)
            "northeast": 1.15, # Northeast
            "west": 1.10,      # Western states
            "south": 0.95,     # Southern states
            "midwest": 1.00,   # Midwest (baseline)
            "default": 1.00
        }
        return multipliers.get(region.lower(), 1.00)


class PricingValidator:
    """Validates pricing results."""

    @staticmethod
    def validate_pricing_results(results: List[Dict]) -> List[str]:
        """
        Validate pricing results meet schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        required_fields = [
            "material_id", "product_name", "quantity", "unit",
            "unit_price", "total_price", "source", "confidence"
        ]

        for i, price in enumerate(results):
            # Check required fields
            for field in required_fields:
                if field not in price:
                    errors.append(f"Pricing {i}: missing field '{field}'")

            # Validate numeric fields
            if price.get("quantity", 0) <= 0:
                errors.append(f"Pricing {i}: invalid quantity {price.get('quantity')}")

            if price.get("unit_price", 0) < 0:
                errors.append(f"Pricing {i}: negative unit_price {price.get('unit_price')}")

            if price.get("total_price", 0) < 0:
                errors.append(f"Pricing {i}: negative total_price {price.get('total_price')}")

            # Validate confidence
            if not (0 <= price.get("confidence", -1) <= 1):
                errors.append(f"Pricing {i}: confidence out of range")

            # Validate source
            valid_sources = {"home_depot", "lowes", "estimationpro", "fallback"}
            if price.get("source", "").lower() not in valid_sources:
                errors.append(f"Pricing {i}: invalid source '{price.get('source')}'")

        return errors


if __name__ == "__main__":
    print("✓ Material Matching → Pricing integration module ready")
