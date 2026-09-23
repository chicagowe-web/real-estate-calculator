"""
Labor calculation service using ICC building code standards.

Calculates labor hours and costs based on:
- Category (framing, electrical, plumbing, etc.)
- Material quantities
- Regional wage rates
- Complexity multipliers
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LaborConfig:
    """Configuration for labor calculation."""
    base_hours_per_100sqft: Dict[str, float] = None
    regional_wage_rates: Dict[str, Dict[str, float]] = None
    complexity_multipliers: Dict[str, float] = None

    def __post_init__(self):
        if not self.base_hours_per_100sqft:
            # ICC building code standard base hours per 100 sqft
            self.base_hours_per_100sqft = {
                "framing": 1.5,
                "electrical": 2.0,
                "plumbing": 2.5,
                "hvac": 2.2,
                "drywall": 1.8,
                "painting": 1.2,
                "flooring": 1.5,
                "roofing": 3.0,
                "masonry": 2.8,
                "carpentry": 1.6,
            }

        if not self.regional_wage_rates:
            # Regional wage rates by trade ($/hr)
            self.regional_wage_rates = {
                "ca": {
                    "framing": 75, "electrical": 85, "plumbing": 80,
                    "hvac": 78, "drywall": 65, "painting": 60,
                    "flooring": 65, "roofing": 75, "masonry": 70
                },
                "ny": {
                    "framing": 70, "electrical": 80, "plumbing": 75,
                    "hvac": 73, "drywall": 60, "painting": 55,
                    "flooring": 60, "roofing": 70, "masonry": 65
                },
                "midwest": {
                    "framing": 45, "electrical": 55, "plumbing": 52,
                    "hvac": 50, "drywall": 40, "painting": 35,
                    "flooring": 40, "roofing": 50, "masonry": 48
                },
                "south": {
                    "framing": 40, "electrical": 48, "plumbing": 45,
                    "hvac": 44, "drywall": 35, "painting": 30,
                    "flooring": 35, "roofing": 45, "masonry": 42
                },
            }

        if not self.complexity_multipliers:
            self.complexity_multipliers = {
                "simple": 0.8,
                "moderate": 1.0,
                "complex": 1.3,
                "very_complex": 1.6,
            }


class LaborCalculator:
    """Calculates labor hours and costs for construction tasks."""

    def __init__(self, config: LaborConfig = None):
        self.config = config or LaborConfig()

    def estimate_labor(
        self,
        category: str,
        material_quantity: float,
        region: str = "midwest",
        complexity: str = "moderate",
        square_footage: float = 100.0
    ) -> Dict[str, Any]:
        """
        Estimate labor hours and cost.

        Args:
            category: Trade category (framing, electrical, plumbing, etc.)
            material_quantity: Material quantity (for quantity-based calcs)
            region: Region for wage lookup (ca, ny, midwest, south)
            complexity: Complexity level (simple, moderate, complex, very_complex)
            square_footage: Estimated square footage for project area

        Returns:
            Labor estimate dict with hours, rate, total cost
        """
        # Normalize category
        cat = category.lower().strip()
        if cat not in self.config.base_hours_per_100sqft:
            logger.warning(f"Unknown category '{cat}', defaulting to carpentry")
            cat = "carpentry"

        # Get base hours per 100 sqft
        base_hours_per_100 = self.config.base_hours_per_100sqft.get(cat, 1.5)

        # Calculate hours based on square footage
        hours = (square_footage / 100) * base_hours_per_100

        # Apply complexity multiplier
        complexity_factor = self.config.complexity_multipliers.get(
            complexity.lower(), 1.0
        )
        adjusted_hours = hours * complexity_factor

        # Get wage rate for region/category
        wage_rate = self._get_wage_rate(region, cat)

        # Calculate labor cost
        labor_cost = adjusted_hours * wage_rate

        return {
            "category": cat,
            "hours": round(adjusted_hours, 2),
            "wage_rate": wage_rate,
            "total_labor_cost": round(labor_cost, 2),
            "complexity_factor": complexity,
            "base_hours_per_100sqft": base_hours_per_100,
            "square_footage": square_footage,
        }

    def _get_wage_rate(self, region: str, category: str) -> float:
        """Get wage rate for region/category."""
        region_rates = self.config.regional_wage_rates.get(
            region.lower(), self.config.regional_wage_rates.get("midwest")
        )
        return region_rates.get(category.lower(), 45.0)


if __name__ == "__main__":
    print("✓ Labor calculation service ready")
