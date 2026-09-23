"""
Integration: All agents → Agent 1 (API aggregation).

Combines results from agents 2-6 into final BlueprintAnalysisResponse.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseAggregator:
    """Aggregates all agent outputs into final response."""

    async def aggregate(
        self,
        estimate_id: str,
        materials: List[Dict],
        pricing: List[Dict],
        labor: List[Dict],
        blueprint_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Combine all outputs into BlueprintAnalysisResponse.

        Args:
            estimate_id: Estimate identifier
            materials: From Claude Vision → Material Matching
            pricing: From Material Matching → Pricing
            labor: From Pricing → Labor Calculation
            blueprint_metadata: Optional metadata (area, location, etc.)

        Returns:
            Complete BlueprintAnalysisResponse
        """
        blueprint_metadata = blueprint_metadata or {}

        logger.info(f"Aggregating results for {estimate_id}")
        logger.debug(f"  Materials: {len(materials)}")
        logger.debug(f"  Pricing: {len(pricing)}")
        logger.debug(f"  Labor: {len(labor)}")

        # Calculate totals
        total_material_cost = sum(p.get("total_price", 0) for p in pricing)
        total_labor_cost = sum(l.get("total_labor_cost", 0) for l in labor)

        # Build response
        response = {
            "estimate_id": estimate_id,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "materials": materials,
            "pricing": pricing,
            "labor": labor,
            "summary": {
                "total_material_cost": round(total_material_cost, 2),
                "total_labor_cost": round(total_labor_cost, 2),
                "total_estimated_cost": round(total_material_cost + total_labor_cost, 2),
                "confidence_score": self._calculate_confidence(materials, pricing, labor),
                "material_categories": self._breakdown_by_category(pricing),
                "labor_by_category": self._breakdown_labor_by_category(labor),
                "material_count": len(materials),
                "labor_categories": len(labor),
                "contingency_amount": round(
                    (total_material_cost * 0.15) + (total_labor_cost * 0.10), 2
                ),
                "estimated_total_with_contingency": round(
                    (total_material_cost + total_labor_cost) * 1.15, 2
                ),
            },
            "metadata": {
                "square_footage": blueprint_metadata.get("square_footage", None),
                "location": blueprint_metadata.get("location", None),
                "blueprint_source": blueprint_metadata.get("blueprint_source", None),
                "upload_timestamp": blueprint_metadata.get("upload_timestamp", None),
            },
            "quality_metrics": {
                "material_confidence": self._material_confidence(materials),
                "pricing_confidence": self._pricing_confidence(pricing),
                "labor_confidence": self._labor_confidence(labor),
                "overall_confidence": self._calculate_confidence(materials, pricing, labor),
            }
        }

        logger.info(
            f"Aggregation complete: ${response['summary']['total_estimated_cost']:.2f} "
            f"(confidence: {response['quality_metrics']['overall_confidence']:.1%})"
        )

        return response

    def _calculate_confidence(
        self,
        materials: List[Dict],
        pricing: List[Dict],
        labor: List[Dict]
    ) -> float:
        """Calculate weighted average confidence across all agents."""
        scores = []

        # Material extraction confidence
        for m in materials:
            scores.append(m.get("combined_confidence", m.get("confidence", 0.8)))

        # Pricing confidence
        for p in pricing:
            scores.append(p.get("confidence", 0.8))

        # Labor estimation is deterministic, high confidence
        for l in labor:
            scores.append(0.95)  # ICC standards are reliable

        avg = sum(scores) / len(scores) if scores else 0.0
        return round(min(avg, 1.0), 2)

    def _material_confidence(self, materials: List[Dict]) -> float:
        """Average confidence for material extraction."""
        if not materials:
            return 0.0
        confidences = [
            m.get("combined_confidence", m.get("confidence", 0.8))
            for m in materials
        ]
        return round(sum(confidences) / len(confidences), 2)

    def _pricing_confidence(self, pricing: List[Dict]) -> float:
        """Average confidence for pricing."""
        if not pricing:
            return 0.0
        confidences = [p.get("confidence", 0.8) for p in pricing]
        return round(sum(confidences) / len(confidences), 2)

    def _labor_confidence(self, labor: List[Dict]) -> float:
        """Labor estimation confidence (deterministic, high)."""
        if not labor:
            return 0.0
        # Labor is based on ICC standards, deterministic
        return 0.95

    @staticmethod
    def _breakdown_by_category(pricing: List[Dict]) -> Dict[str, float]:
        """Group pricing totals by material category."""
        categories = {}
        for p in pricing:
            category = p.get("category", "other")
            categories[category] = categories.get(category, 0) + p.get("total_price", 0)

        # Round all values
        return {cat: round(cost, 2) for cat, cost in categories.items()}

    @staticmethod
    def _breakdown_labor_by_category(labor: List[Dict]) -> Dict[str, float]:
        """Group labor costs by trade category."""
        categories = {}
        for l in labor:
            category = l.get("category", "other")
            categories[category] = categories.get(category, 0) + l.get("total_labor_cost", 0)

        # Round all values
        return {cat: round(cost, 2) for cat, cost in categories.items()}


class AggregationValidator:
    """Validates aggregated responses."""

    @staticmethod
    def validate_aggregated_response(response: Dict) -> List[str]:
        """
        Validate aggregated response meets schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        required_fields = [
            "estimate_id", "status", "timestamp", "materials", "pricing",
            "labor", "summary", "quality_metrics"
        ]

        # Check required top-level fields
        for field in required_fields:
            if field not in response:
                errors.append(f"Response: missing field '{field}'")

        # Validate summary fields
        summary = response.get("summary", {})
        summary_fields = [
            "total_material_cost", "total_labor_cost", "total_estimated_cost",
            "confidence_score", "material_categories", "labor_by_category"
        ]
        for field in summary_fields:
            if field not in summary:
                errors.append(f"Summary: missing field '{field}'")

        # Validate numeric fields
        if response.get("summary", {}).get("total_estimated_cost", 0) < 0:
            errors.append("Summary: negative total_estimated_cost")

        if not (0 <= response.get("summary", {}).get("confidence_score", -1) <= 1):
            errors.append("Summary: confidence_score out of range")

        return errors


if __name__ == "__main__":
    print("✓ API aggregation module ready")
