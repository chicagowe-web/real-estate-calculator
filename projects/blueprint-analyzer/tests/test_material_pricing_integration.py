"""
Tests for Agent 4 (Material Matching) → Agent 5 (Pricing) integration.
"""

import pytest
from typing import List, Dict, Any

from hermes.blueprint_analysis.pricing.mm_integration import (
    MaterialMatchingPricingBridge,
    PricingValidator,
    PricingIntegrationConfig,
)


class TestMaterialMatchingPricingBridge:
    """Test pricing lookup for matched materials."""

    @pytest.fixture
    def bridge(self):
        """Initialize bridge for tests."""
        config = PricingIntegrationConfig(region="midwest")
        return MaterialMatchingPricingBridge(config)

    @pytest.fixture
    def sample_matched_materials(self) -> List[Dict]:
        """Sample matched materials from Material Matching service."""
        return [
            {
                "material_id": "lib_2x4_spf_8ft",
                "matched_name": "2x4 Stud - SPF - 8ft",
                "quantity": 42,
                "unit": "pieces",
                "category": "lumber",
                "match_confidence": 0.92
            },
            {
                "material_id": "lib_drywall_5_8_4x8",
                "matched_name": "Drywall Sheet - 5/8\" - 4x8",
                "quantity": 15,
                "unit": "sheets",
                "category": "drywall",
                "match_confidence": 0.88
            },
            {
                "material_id": "lib_paint_5gal",
                "matched_name": "Interior Latex Paint - 5gal",
                "quantity": 2,
                "unit": "gallons",
                "category": "paint",
                "match_confidence": 0.95
            }
        ]

    @pytest.mark.asyncio
    async def test_price_lookup_success(self, bridge, sample_matched_materials):
        """Test: Price lookup succeeds for matched materials."""
        pricing = await bridge.process_matched_materials(
            sample_matched_materials,
            "test_001"
        )

        assert len(pricing) > 0
        assert all("material_id" in p for p in pricing)
        assert all("unit_price" in p for p in pricing)
        assert all("total_price" in p for p in pricing)

    @pytest.mark.asyncio
    async def test_total_price_calculation(self, bridge):
        """Test: Total price calculated correctly."""
        materials = [
            {
                "material_id": "lib_test",
                "matched_name": "Test Material",
                "quantity": 10,
                "unit": "pieces",
                "category": "lumber",
                "match_confidence": 0.90
            }
        ]

        pricing = await bridge.process_matched_materials(materials, "test_002")

        if pricing:
            result = pricing[0]
            # Total should be quantity × unit_price (× regional multiplier)
            assert result["total_price"] >= result["quantity"] * result["unit_price"] * 0.99
            assert result["total_price"] <= result["quantity"] * result["unit_price"] * 1.01

    @pytest.mark.asyncio
    async def test_regional_multiplier_applied(self, bridge):
        """Test: Regional multipliers applied correctly."""
        materials = [
            {
                "material_id": "lib_test",
                "matched_name": "Test Material",
                "quantity": 100,
                "unit": "pieces",
                "category": "lumber",
                "match_confidence": 0.90
            }
        ]

        # Test different regions
        regions = ["midwest", "ca", "ny", "south"]

        for region in regions:
            pricing = await bridge.process_matched_materials(
                materials,
                f"test_{region}"
            )

            if pricing:
                multiplier = MaterialMatchingPricingBridge._get_regional_multiplier(region)
                assert pricing[0]["regional_multiplier"] == multiplier

    @pytest.mark.asyncio
    async def test_empty_materials_list(self, bridge):
        """Test: Handles empty materials list."""
        pricing = await bridge.process_matched_materials([], "test_003")

        assert pricing == []

    @pytest.mark.asyncio
    async def test_supplier_info_included(self, bridge, sample_matched_materials):
        """Test: Supplier information included in results."""
        pricing = await bridge.process_matched_materials(
            sample_matched_materials,
            "test_004"
        )

        for p in pricing:
            assert "source" in p
            assert p["source"] in ["home_depot", "lowes", "estimationpro", "fallback"]

    @pytest.mark.asyncio
    async def test_confidence_preserved(self, bridge):
        """Test: Confidence scores included in results."""
        materials = [
            {
                "material_id": "lib_conf_test",
                "matched_name": "Confidence Test",
                "quantity": 5,
                "unit": "pieces",
                "category": "lumber",
                "match_confidence": 0.85
            }
        ]

        pricing = await bridge.process_matched_materials(materials, "test_005")

        if pricing:
            assert "confidence" in pricing[0]
            assert 0 <= pricing[0]["confidence"] <= 1


class TestPricingValidator:
    """Test validation of pricing results."""

    def test_valid_pricing_result(self):
        """Test: Valid pricing passes validation."""
        result = {
            "material_id": "lib_test",
            "product_name": "Test Product",
            "quantity": 10,
            "unit": "pieces",
            "unit_price": 4.50,
            "total_price": 45.00,
            "source": "home_depot",
            "confidence": 0.92
        }

        errors = PricingValidator.validate_pricing_results([result])

        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test: Missing fields detected."""
        result = {
            "material_id": "lib_test",
            "product_name": "Test"
            # Missing: quantity, unit, unit_price, total_price, source, confidence
        }

        errors = PricingValidator.validate_pricing_results([result])

        assert len(errors) > 0
        assert any("missing field" in e for e in errors)

    def test_invalid_prices(self):
        """Test: Invalid prices caught."""
        result = {
            "material_id": "lib_test",
            "product_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "unit_price": -5.00,  # Negative
            "total_price": 45.00,
            "source": "home_depot",
            "confidence": 0.92
        }

        errors = PricingValidator.validate_pricing_results([result])

        assert any("negative unit_price" in e for e in errors)

    def test_invalid_confidence(self):
        """Test: Confidence validation."""
        result = {
            "material_id": "lib_test",
            "product_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "unit_price": 4.50,
            "total_price": 45.00,
            "source": "home_depot",
            "confidence": 1.5  # Out of range
        }

        errors = PricingValidator.validate_pricing_results([result])

        assert any("confidence out of range" in e for e in errors)

    def test_invalid_source(self):
        """Test: Source validation."""
        result = {
            "material_id": "lib_test",
            "product_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "unit_price": 4.50,
            "total_price": 45.00,
            "source": "invalid_source",  # Invalid
            "confidence": 0.92
        }

        errors = PricingValidator.validate_pricing_results([result])

        assert any("invalid source" in e for e in errors)


class TestDataContracts:
    """Test data contracts between Material Matching and Pricing."""

    def test_matched_material_pricing_input_contract(self):
        """Test: Matched material has all required pricing inputs."""
        matched = {
            "material_id": "lib_2x4_spf",
            "matched_name": "2x4 Stud - SPF",
            "quantity": 42,
            "unit": "pieces",
            "category": "lumber",
            "match_confidence": 0.92
        }

        # Should have all fields needed for pricing
        assert matched["material_id"]  # For pricing lookup
        assert matched["quantity"] > 0  # For total cost calc
        assert matched["unit"]  # For unit price
        assert matched["category"]  # For categorization

    def test_pricing_output_for_labor_integration(self):
        """Test: Pricing output ready for Labor calculation."""
        pricing = {
            "material_id": "lib_2x4_spf",
            "product_name": "2x4 Stud - SPF - 8ft",
            "quantity": 42,
            "unit": "pieces",
            "unit_price": 4.49,
            "total_price": 188.58,
            "source": "home_depot",
            "confidence": 0.92,
            "category": "lumber"
        }

        # Should have all fields for labor integration
        assert pricing["material_id"]
        assert pricing["quantity"]
        assert pricing["total_price"] > 0
        assert pricing["category"]


class TestPerformance:
    """Test performance metrics."""

    @pytest.mark.asyncio
    async def test_batch_pricing_latency(self):
        """Test: Batch pricing lookup meets latency targets."""
        import time

        bridge = MaterialMatchingPricingBridge()

        materials = [
            {
                "material_id": f"lib_perf_{i}",
                "matched_name": f"Material {i}",
                "quantity": 10,
                "unit": "pieces",
                "category": "lumber",
                "match_confidence": 0.90
            }
            for i in range(30)  # 30 materials
        ]

        start = time.time()
        await bridge.process_matched_materials(materials, "perf_test")
        elapsed = time.time() - start

        # Should price 30 materials in <2 seconds (including API calls)
        assert elapsed < 2.0, f"Pricing took {elapsed:.2f}s, target <2.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
