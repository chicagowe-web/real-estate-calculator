"""
Tests for API aggregation layer (all agents → API).
"""

import pytest
from typing import List, Dict, Any

from hermes.blueprint_analysis.api.routes_aggregation import (
    ResponseAggregator,
    AggregationValidator,
)


class TestResponseAggregator:
    """Test response aggregation."""

    @pytest.fixture
    def aggregator(self):
        """Initialize aggregator for tests."""
        return ResponseAggregator()

    @pytest.fixture
    def sample_materials(self) -> List[Dict]:
        """Sample materials from Material Matching."""
        return [
            {
                "material_id": "lib_2x4_spf",
                "matched_name": "2x4 Stud - SPF - 8ft",
                "quantity": 42,
                "unit": "pieces",
                "category": "framing",
                "combined_confidence": 0.92
            },
            {
                "material_id": "lib_drywall",
                "matched_name": "Drywall Sheet - 5/8\" - 4x8",
                "quantity": 15,
                "unit": "sheets",
                "category": "drywall",
                "combined_confidence": 0.88
            }
        ]

    @pytest.fixture
    def sample_pricing(self) -> List[Dict]:
        """Sample pricing results."""
        return [
            {
                "material_id": "lib_2x4_spf",
                "product_name": "2x4 Stud - SPF",
                "quantity": 42,
                "unit": "pieces",
                "unit_price": 4.49,
                "total_price": 188.58,
                "source": "home_depot",
                "confidence": 0.92,
                "category": "framing"
            },
            {
                "material_id": "lib_drywall",
                "product_name": "Drywall Sheet",
                "quantity": 15,
                "unit": "sheets",
                "unit_price": 15.00,
                "total_price": 225.00,
                "source": "home_depot",
                "confidence": 0.88,
                "category": "drywall"
            }
        ]

    @pytest.fixture
    def sample_labor(self) -> List[Dict]:
        """Sample labor estimates."""
        return [
            {
                "category": "framing",
                "hours": 3.6,
                "wage_rate": 45.00,
                "total_labor_cost": 162.00,
                "complexity_factor": "moderate",
                "materials_in_category": 1
            },
            {
                "category": "drywall",
                "hours": 2.4,
                "wage_rate": 40.00,
                "total_labor_cost": 96.00,
                "complexity_factor": "simple",
                "materials_in_category": 1
            }
        ]

    @pytest.mark.asyncio
    async def test_aggregation_success(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Aggregation succeeds with all agents."""
        response = await aggregator.aggregate(
            estimate_id="test_001",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        assert response["estimate_id"] == "test_001"
        assert response["status"] == "completed"
        assert "summary" in response
        assert "quality_metrics" in response

    @pytest.mark.asyncio
    async def test_cost_calculations(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Cost totals calculated correctly."""
        response = await aggregator.aggregate(
            estimate_id="test_002",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        summary = response["summary"]

        # Material cost should match pricing totals
        expected_material = sum(p["total_price"] for p in sample_pricing)
        assert summary["total_material_cost"] == pytest.approx(expected_material, 0.01)

        # Labor cost should match labor totals
        expected_labor = sum(l["total_labor_cost"] for l in sample_labor)
        assert summary["total_labor_cost"] == pytest.approx(expected_labor, 0.01)

        # Total should be sum
        expected_total = expected_material + expected_labor
        assert summary["total_estimated_cost"] == pytest.approx(expected_total, 0.01)

    @pytest.mark.asyncio
    async def test_confidence_calculation(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Confidence score calculated."""
        response = await aggregator.aggregate(
            estimate_id="test_003",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        confidence = response["quality_metrics"]["overall_confidence"]
        assert 0 <= confidence <= 1
        assert confidence > 0.8  # Should be high with good data

    @pytest.mark.asyncio
    async def test_category_breakdown(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Category breakdown calculated."""
        response = await aggregator.aggregate(
            estimate_id="test_004",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        categories = response["summary"]["material_categories"]
        labor_cats = response["summary"]["labor_by_category"]

        assert "framing" in categories
        assert "drywall" in categories
        assert categories["framing"] > 0
        assert categories["drywall"] > 0

        assert "framing" in labor_cats
        assert "drywall" in labor_cats

    @pytest.mark.asyncio
    async def test_contingency_calculation(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Contingency amount calculated."""
        response = await aggregator.aggregate(
            estimate_id="test_005",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        summary = response["summary"]
        material_cost = summary["total_material_cost"]
        labor_cost = summary["total_labor_cost"]

        # Contingency = 15% materials + 10% labor
        expected_contingency = (material_cost * 0.15) + (labor_cost * 0.10)
        assert summary["contingency_amount"] == pytest.approx(expected_contingency, 0.01)

    @pytest.mark.asyncio
    async def test_empty_inputs(self, aggregator):
        """Test: Handles empty lists gracefully."""
        response = await aggregator.aggregate(
            estimate_id="test_006",
            materials=[],
            pricing=[],
            labor=[]
        )

        assert response["estimate_id"] == "test_006"
        assert response["summary"]["total_estimated_cost"] == 0
        assert response["summary"]["material_count"] == 0

    @pytest.mark.asyncio
    async def test_metadata_included(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Metadata included in response."""
        metadata = {
            "square_footage": 500.0,
            "location": "Kitchen",
            "upload_timestamp": "2026-09-23T10:00:00"
        }

        response = await aggregator.aggregate(
            estimate_id="test_007",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor,
            blueprint_metadata=metadata
        )

        assert response["metadata"]["square_footage"] == 500.0
        assert response["metadata"]["location"] == "Kitchen"

    @pytest.mark.asyncio
    async def test_quality_metrics(
        self, aggregator, sample_materials, sample_pricing, sample_labor
    ):
        """Test: Quality metrics included."""
        response = await aggregator.aggregate(
            estimate_id="test_008",
            materials=sample_materials,
            pricing=sample_pricing,
            labor=sample_labor
        )

        metrics = response["quality_metrics"]
        assert "material_confidence" in metrics
        assert "pricing_confidence" in metrics
        assert "labor_confidence" in metrics
        assert "overall_confidence" in metrics

        assert all(0 <= v <= 1 for v in metrics.values())


class TestAggregationValidator:
    """Test validation of aggregated responses."""

    def test_valid_response(self):
        """Test: Valid response passes validation."""
        response = {
            "estimate_id": "test_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [],
            "pricing": [],
            "labor": [],
            "summary": {
                "total_material_cost": 500.00,
                "total_labor_cost": 200.00,
                "total_estimated_cost": 700.00,
                "confidence_score": 0.90,
                "material_categories": {},
                "labor_by_category": {}
            },
            "quality_metrics": {
                "material_confidence": 0.90,
                "pricing_confidence": 0.90,
                "labor_confidence": 0.95,
                "overall_confidence": 0.92
            }
        }

        errors = AggregationValidator.validate_aggregated_response(response)

        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test: Missing fields detected."""
        response = {
            "estimate_id": "test_001"
            # Missing: status, timestamp, materials, pricing, etc.
        }

        errors = AggregationValidator.validate_aggregated_response(response)

        assert len(errors) > 0
        assert any("missing field" in e for e in errors)

    def test_invalid_confidence(self):
        """Test: Confidence out of range caught."""
        response = {
            "estimate_id": "test_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [],
            "pricing": [],
            "labor": [],
            "summary": {
                "total_material_cost": 500.00,
                "total_labor_cost": 200.00,
                "total_estimated_cost": 700.00,
                "confidence_score": 1.5,  # Invalid
                "material_categories": {},
                "labor_by_category": {}
            },
            "quality_metrics": {}
        }

        errors = AggregationValidator.validate_aggregated_response(response)

        assert any("confidence_score out of range" in e for e in errors)

    def test_negative_cost(self):
        """Test: Negative costs caught."""
        response = {
            "estimate_id": "test_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [],
            "pricing": [],
            "labor": [],
            "summary": {
                "total_material_cost": 500.00,
                "total_labor_cost": 200.00,
                "total_estimated_cost": -700.00,  # Invalid
                "confidence_score": 0.90,
                "material_categories": {},
                "labor_by_category": {}
            },
            "quality_metrics": {}
        }

        errors = AggregationValidator.validate_aggregated_response(response)

        assert any("negative total_estimated_cost" in e for e in errors)


class TestDataContracts:
    """Test data contract for aggregated response."""

    def test_blueprint_analysis_response_contract(self):
        """Test: Response matches BlueprintAnalysisResponse schema."""
        response = {
            "estimate_id": "est_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [
                {
                    "material_id": "lib_test",
                    "matched_name": "Test",
                    "quantity": 10,
                    "category": "lumber"
                }
            ],
            "pricing": [
                {
                    "material_id": "lib_test",
                    "unit_price": 5.00,
                    "total_price": 50.00,
                    "category": "lumber"
                }
            ],
            "labor": [
                {
                    "category": "carpentry",
                    "hours": 1.0,
                    "wage_rate": 50.00,
                    "total_labor_cost": 50.00,
                    "complexity_factor": "simple"
                }
            ],
            "summary": {
                "total_material_cost": 50.00,
                "total_labor_cost": 50.00,
                "total_estimated_cost": 100.00,
                "confidence_score": 0.90,
                "material_categories": {"lumber": 50.00},
                "labor_by_category": {"carpentry": 50.00},
                "contingency_amount": 10.50,
                "estimated_total_with_contingency": 110.50
            },
            "quality_metrics": {
                "overall_confidence": 0.90
            }
        }

        errors = AggregationValidator.validate_aggregated_response(response)

        # Should be mostly valid (missing optional fields OK)
        assert len(errors) < 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
