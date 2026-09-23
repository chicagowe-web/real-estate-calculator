"""
Integration between Agent 5 (Pricing) → Agent 6 (Labor Calculation).

Flow: Pricing results → Category aggregation → Labor calculation → Return labor estimates
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from .service import LaborCalculator, LaborConfig


logger = logging.getLogger(__name__)


@dataclass
class LaborIntegrationConfig:
    """Configuration for labor integration."""
    region: str = "midwest"
    default_complexity: str = "moderate"
    labor_config: LaborConfig = None


class PricingLaborBridge:
    """
    Orchestrates data flow from Pricing → Labor Calculation.

    Takes pricing results and:
    1. Groups materials by category/trade
    2. Estimates square footage from material quantities
    3. Calculates labor hours and costs
    4. Returns labor breakdown by trade
    """

    def __init__(self, config: LaborIntegrationConfig = None):
        self.config = config or LaborIntegrationConfig()
        self.calculator = LaborCalculator(self.config.labor_config)

    async def process_pricing_results(
        self,
        pricing_results: List[Dict[str, Any]],
        estimate_id: str,
        region: str = None,
        blueprint_area_sqft: float = 100.0
    ) -> List[Dict[str, Any]]:
        """
        Calculate labor costs for priced materials.

        Args:
            pricing_results: Output from Pricing service
            estimate_id: ID for logging/tracking
            region: Optional region override (uses config default otherwise)
            blueprint_area_sqft: Estimated blueprint square footage

        Returns:
            List of labor estimates by category/trade

        Raises:
            ValueError: If input validation fails
        """
        if not pricing_results:
            logger.warning(f"No pricing results for labor calculation {estimate_id}")
            return []

        region = region or self.config.region
        logger.info(f"Calculating labor for {len(pricing_results)} materials ({region})")

        # Group materials by category
        categories = self._group_by_category(pricing_results)
        logger.debug(f"Grouped into {len(categories)} categories: {list(categories.keys())}")

        labor_estimates = []
        failed_estimates = []

        for category, materials in categories.items():
            try:
                # Estimate labor for this category
                estimate = await self._estimate_category_labor(
                    category=category,
                    materials=materials,
                    region=region,
                    blueprint_area_sqft=blueprint_area_sqft,
                    estimate_id=estimate_id
                )

                if estimate:
                    labor_estimates.append(estimate)
                else:
                    failed_estimates.append(category)

            except Exception as e:
                logger.error(f"Labor estimation failed for '{category}': {e}")
                failed_estimates.append(category)
                # Continue with next category (graceful degradation)
                continue

        # Log summary
        logger.info(f"Estimated labor for {len(labor_estimates)}/{len(categories)} categories for {estimate_id}")
        if failed_estimates:
            logger.warning(f"Failed labor estimates ({len(failed_estimates)}): {failed_estimates}")

        return labor_estimates

    async def _estimate_category_labor(
        self,
        category: str,
        materials: List[Dict[str, Any]],
        region: str,
        blueprint_area_sqft: float,
        estimate_id: str
    ) -> Dict[str, Any]:
        """
        Estimate labor for single category.

        Returns labor estimate dict with hours, rate, total cost.
        """
        if not materials:
            return None

        # Calculate total quantity for this category
        total_quantity = sum(m.get("quantity", 0) for m in materials)
        if total_quantity <= 0:
            logger.warning(f"Invalid quantity for {category}: {total_quantity}")
            return None

        # Determine complexity based on material count and quantities
        complexity = self._assess_complexity(len(materials), total_quantity)

        # Calculate labor estimate
        estimate = self.calculator.estimate_labor(
            category=category,
            material_quantity=total_quantity,
            region=region,
            complexity=complexity,
            square_footage=blueprint_area_sqft
        )

        # Add context information
        estimate.update({
            "materials_in_category": len(materials),
            "total_material_quantity": total_quantity,
            "region": region,
            "estimate_id": estimate_id,
            "material_ids": [m.get("material_id") for m in materials],
        })

        return estimate

    @staticmethod
    def _group_by_category(pricing_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group materials by category."""
        categories = {}
        for material in pricing_results:
            category = material.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(material)
        return categories

    @staticmethod
    def _assess_complexity(material_count: int, total_quantity: float) -> str:
        """Assess project complexity based on material metrics."""
        # Simple heuristic based on material diversity and quantity
        if material_count <= 3 and total_quantity < 50:
            return "simple"
        elif material_count <= 8 and total_quantity < 150:
            return "moderate"
        elif material_count <= 15 and total_quantity < 300:
            return "complex"
        else:
            return "very_complex"


class LaborValidator:
    """Validates labor calculation results."""

    @staticmethod
    def validate_labor_estimates(estimates: List[Dict]) -> List[str]:
        """
        Validate labor estimates meet schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        required_fields = [
            "category", "hours", "wage_rate", "total_labor_cost", "complexity_factor"
        ]

        for i, estimate in enumerate(estimates):
            # Check required fields
            for field in required_fields:
                if field not in estimate:
                    errors.append(f"Labor {i}: missing field '{field}'")

            # Validate numeric fields
            if estimate.get("hours", 0) < 0:
                errors.append(f"Labor {i}: negative hours {estimate.get('hours')}")

            if estimate.get("wage_rate", 0) < 0:
                errors.append(f"Labor {i}: negative wage_rate {estimate.get('wage_rate')}")

            if estimate.get("total_labor_cost", 0) < 0:
                errors.append(f"Labor {i}: negative total_labor_cost {estimate.get('total_labor_cost')}")

            # Validate complexity factor
            valid_complexities = {"simple", "moderate", "complex", "very_complex"}
            if estimate.get("complexity_factor", "").lower() not in valid_complexities:
                errors.append(f"Labor {i}: invalid complexity_factor '{estimate.get('complexity_factor')}'")

        return errors


if __name__ == "__main__":
    print("✓ Pricing → Labor integration module ready")
