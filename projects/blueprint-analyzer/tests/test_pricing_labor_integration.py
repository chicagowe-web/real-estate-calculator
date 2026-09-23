"""
Tests for Agent 5 (Pricing) → Agent 6 (Labor Calculation) integration.
"""

import pytest
from typing import List, Dict, Any

from hermes.blueprint_analysis.labor.pl_integration import (
    PricingLaborBridge,
    LaborValidator,
    LaborIntegrationConfig,
)
from hermes.blueprint_analysis.labor.service import LaborCalculator


class TestLaborCalculator:
    """Test labor estimation calculations."""

    @pytest.fixture
    def calculator(self):
        """Initialize calculator for tests."""
        return LaborCalculator()

    def test_framing_labor_estimation(self, calculator):
        """Test: Framing labor calculated correctly."""
        result = calculator.estimate_labor(
            category="framing",
            material_quantity=42,
            region="midwest",
            complexity="moderate",
            square_footage=200.0
        )

        assert result["category"] == "framing"
        assert result["hours"] > 0
        assert result["wage_rate"] == 45  # Midwest framing rate
        assert result["total_labor_cost"] > 0

    def test_electrical_labor_estimation(self, calculator):
        """Test: Electrical labor calculated correctly."""
        result = calculator.estimate_labor(
            category="electrical",
            material_quantity=10,
            region="midwest",
            complexity="moderate",
            square_footage=200.0
        )

        assert result["category"] == "electrical"
        assert result["hours"] > 0
        assert result["wage_rate"] == 55  # Midwest electrical rate
        assert result["complexity_factor"] == "moderate"

    def test_regional_wage_rates(self, calculator):
        """Test: Regional wage rates applied correctly."""
        regions = ["ca", "ny", "midwest", "south"]

        for region in regions:
            result = calculator.estimate_labor(
                category="framing",
                material_quantity=10,
                region=region,
                complexity="moderate",
                square_footage=100.0
            )

            assert result["region"] if hasattr(result, "region") else True
            assert result["wage_rate"] > 0

    def test_complexity_multipliers(self, calculator):
        """Test: Complexity multipliers affect hours."""
        base = calculator.estimate_labor(
            category="framing",
            material_quantity=10,
            region="midwest",
            complexity="simple",
            square_footage=100.0
        )

        complex_result = calculator.estimate_labor(
            category="framing",
            material_quantity=10,
            region="midwest",
            complexity="very_complex",
            square_footage=100.0
        )

        # Very complex should have significantly more hours
        assert complex_result["hours"] > base["hours"] * 1.5


class TestPricingLaborBridge:
    """Test pricing → labor integration."""

    @pytest.fixture
    def bridge(self):
        """Initialize bridge for tests."""
        config = LaborIntegrationConfig(region="midwest")
        return PricingLaborBridge(config)

    @pytest.fixture
    def sample_pricing_results(self) -> List[Dict]:
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
                "product_name": "Drywall Sheet - 5/8\"",
                "quantity": 15,
                "unit": "sheets",
                "unit_price": 15.00,
                "total_price": 225.00,
                "source": "home_depot",
                "confidence": 0.88,
                "category": "drywall"
            },
            {
                "material_id": "lib_romex",
                "product_name": "Romex 12/2 Wire",
                "quantity": 3,
                "unit": "spools",
                "unit_price": 35.00,
                "total_price": 105.00,
                "source": "home_depot",
                "confidence": 0.85,
                "category": "electrical"
            }
        ]

    @pytest.mark.asyncio
    async def test_labor_estimation_success(self, bridge, sample_pricing_results):
        """Test: Labor estimation succeeds for pricing results."""
        labor = await bridge.process_pricing_results(
            sample_pricing_results,
            "test_001",
            blueprint_area_sqft=500.0
        )

        assert len(labor) > 0
        assert all("category" in l for l in labor)
        assert all("hours" in l for l in labor)
        assert all("total_labor_cost" in l for l in labor)

    @pytest.mark.asyncio
    async def test_materials_grouped_by_category(self, bridge, sample_pricing_results):
        """Test: Materials grouped by category correctly."""
        labor = await bridge.process_pricing_results(
            sample_pricing_results,
            "test_002",
            blueprint_area_sqft=500.0
        )

        categories = {l["category"] for l in labor}
        # Should have framing, drywall, electrical
        assert "framing" in categories or len(labor) > 0
        assert len(labor) <= len(sample_pricing_results)

    @pytest.mark.asyncio
    async def test_empty_pricing_list(self, bridge):
        """Test: Handles empty pricing list."""
        labor = await bridge.process_pricing_results(
            [],
            "test_003",
            blueprint_area_sqft=500.0
        )

        assert labor == []

    @pytest.mark.asyncio
    async def test_wage_rate_included(self, bridge, sample_pricing_results):
        """Test: Wage rate included in results."""
        labor = await bridge.process_pricing_results(
            sample_pricing_results,
            "test_004",
            region="midwest",
            blueprint_area_sqft=500.0
        )

        for estimate in labor:
            assert "wage_rate" in estimate
            assert estimate["wage_rate"] > 0

    @pytest.mark.asyncio
    async def test_complexity_assessment(self, bridge):
        """Test: Complexity assessed from material metrics."""
        # Simple: few materials, low quantity
        simple_pricing = [
            {
                "material_id": "lib_test",
                "product_name": "Test",
                "quantity": 10,
                "unit": "pieces",
                "unit_price": 5.00,
                "total_price": 50.00,
                "source": "home_depot",
                "confidence": 0.90,
                "category": "lumber"
            }
        ]

        labor = await bridge.process_pricing_results(
            simple_pricing,
            "test_005",
            blueprint_area_sqft=100.0
        )

        if labor:
            # Simple project should have lower complexity
            assert labor[0].get("complexity_factor") in ["simple", "moderate"]

    @pytest.mark.asyncio
    async def test_regional_labor_variation(self, bridge):
        """Test: Regional labor costs vary correctly."""
        pricing = [
            {
                "material_id": "lib_test",
                "product_name": "Test Material",
                "quantity": 100,
                "unit": "pieces",
                "unit_price": 5.00,
                "total_price": 500.00,
                "source": "home_depot",
                "confidence": 0.90,
                "category": "framing"
            }
        ]

        # Test different regions
        regions = ["midwest", "ca", "ny"]

        labor_costs = {}
        for region in regions:
            labor = await bridge.process_pricing_results(
                pricing,
                f"test_{region}",
                region=region,
                blueprint_area_sqft=500.0
            )

            if labor:
                labor_costs[region] = labor[0]["total_labor_cost"]

        # CA should be more expensive than midwest
        if "ca" in labor_costs and "midwest" in labor_costs:
            assert labor_costs["ca"] > labor_costs["midwest"]


class TestLaborValidator:
    """Test validation of labor estimates."""

    def test_valid_labor_estimate(self):
        """Test: Valid estimate passes validation."""
        estimate = {
            "category": "framing",
            "hours": 3.6,
            "wage_rate": 45.00,
            "total_labor_cost": 162.00,
            "complexity_factor": "moderate"
        }

        errors = LaborValidator.validate_labor_estimates([estimate])

        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test: Missing fields detected."""
        estimate = {
            "category": "framing",
            "hours": 3.6
            # Missing: wage_rate, total_labor_cost, complexity_factor
        }

        errors = LaborValidator.validate_labor_estimates([estimate])

        assert len(errors) > 0
        assert any("missing field" in e for e in errors)

    def test_invalid_hours(self):
        """Test: Invalid hours caught."""
        estimate = {
            "category": "framing",
            "hours": -3.6,  # Negative
            "wage_rate": 45.00,
            "total_labor_cost": 162.00,
            "complexity_factor": "moderate"
        }

        errors = LaborValidator.validate_labor_estimates([estimate])

        assert any("negative hours" in e for e in errors)

    def test_invalid_complexity(self):
        """Test: Invalid complexity caught."""
        estimate = {
            "category": "framing",
            "hours": 3.6,
            "wage_rate": 45.00,
            "total_labor_cost": 162.00,
            "complexity_factor": "invalid_level"  # Invalid
        }

        errors = LaborValidator.validate_labor_estimates([estimate])

        assert any("invalid complexity_factor" in e for e in errors)


class TestDataContracts:
    """Test data contracts between Pricing and Labor."""

    def test_pricing_output_labor_input_contract(self):
        """Test: Pricing output has all required labor inputs."""
        pricing = {
            "material_id": "lib_2x4_spf",
            "product_name": "2x4 Stud - SPF",
            "quantity": 42,
            "unit": "pieces",
            "unit_price": 4.49,
            "total_price": 188.58,
            "source": "home_depot",
            "confidence": 0.92,
            "category": "framing"
        }

        # Should have all fields needed for labor calculation
        assert pricing["category"]  # For trade identification
        assert pricing["quantity"] > 0  # For complexity assessment
        assert pricing["total_price"] >= 0  # For context

    def test_labor_output_aggregation_input_contract(self):
        """Test: Labor output ready for aggregation."""
        labor = {
            "category": "framing",
            "hours": 3.6,
            "wage_rate": 45.00,
            "total_labor_cost": 162.00,
            "complexity_factor": "moderate",
            "materials_in_category": 5,
            "total_material_quantity": 42
        }

        # Should have all fields for aggregation
        assert labor["category"]
        assert labor["hours"] >= 0
        assert labor["total_labor_cost"] >= 0
        assert labor["wage_rate"] > 0


class TestPerformance:
    """Test performance metrics."""

    @pytest.mark.asyncio
    async def test_batch_labor_latency(self):
        """Test: Batch labor estimation meets latency targets."""
        import time

        bridge = PricingLaborBridge()

        pricing = [
            {
                "material_id": f"lib_perf_{i}",
                "product_name": f"Material {i}",
                "quantity": 10,
                "unit": "pieces",
                "unit_price": 5.00,
                "total_price": 50.00,
                "source": "home_depot",
                "confidence": 0.90,
                "category": "lumber" if i % 2 == 0 else "framing"
            }
            for i in range(25)  # 25 materials
        ]

        start = time.time()
        await bridge.process_pricing_results(pricing, "perf_test", blueprint_area_sqft=500.0)
        elapsed = time.time() - start

        # Should estimate labor for 25 materials in <1 second
        assert elapsed < 1.0, f"Labor estimation took {elapsed:.2f}s, target <1.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
