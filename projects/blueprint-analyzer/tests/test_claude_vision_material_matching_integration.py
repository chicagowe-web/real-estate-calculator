"""
Tests for Agent 3 (Claude Vision) → Agent 4 (Material Matching) integration.
"""

import pytest
from typing import List

from hermes.blueprint_analysis.models import ExtractedMaterial
from hermes.blueprint_analysis.materials.cv_integration import (
    ClaudeVisionMaterialMatchingBridge,
    MaterialMatchingValidator,
    MatchingConfig,
)


class TestClaudeVisionMaterialMatchingBridge:
    """Test material matching of Claude Vision output."""

    @pytest.fixture
    def bridge(self):
        """Initialize bridge for tests."""
        return ClaudeVisionMaterialMatchingBridge()

    @pytest.fixture
    def sample_extracted_materials(self) -> List[ExtractedMaterial]:
        """Sample materials from Claude Vision."""
        return [
            ExtractedMaterial(
                id="cv_001",
                name="2x4 Stud - SPF - 8ft",
                quantity=42,
                unit="pieces",
                category="lumber",
                confidence=0.94,
                extracted_from="claude_vision",
                specifications={"grade": "2", "species": "SPF"}
            ),
            ExtractedMaterial(
                id="cv_002",
                name="Drywall Sheet - 5/8\" - 4x8",
                quantity=15,
                unit="sheets",
                category="drywall",
                confidence=0.88,
                extracted_from="claude_vision"
            ),
            ExtractedMaterial(
                id="cv_003",
                name="Romex 12/2 Wire - 100ft",
                quantity=3,
                unit="spools",
                category="electrical",
                confidence=0.85,
                extracted_from="claude_vision"
            ),
        ]

    @pytest.mark.asyncio
    async def test_match_common_materials(self, bridge, sample_extracted_materials):
        """Test: Common materials matched against library."""
        matched = await bridge.process_extracted_materials(
            sample_extracted_materials,
            "test_001"
        )

        assert len(matched) > 0
        assert all("material_id" in m for m in matched)
        assert all(m["material_id"].startswith("lib_") for m in matched)

    @pytest.mark.asyncio
    async def test_match_confidence_scores(self, bridge, sample_extracted_materials):
        """Test: Match confidence scores computed."""
        matched = await bridge.process_extracted_materials(
            sample_extracted_materials,
            "test_002"
        )

        for mat in matched:
            assert 0 <= mat.get("match_confidence", 0) <= 1
            assert 0 <= mat.get("extracted_confidence", 0) <= 1
            assert 0 <= mat.get("combined_confidence", 0) <= 1

    @pytest.mark.asyncio
    async def test_unit_conversion(self, bridge):
        """Test: Units converted to standard form."""
        materials = [
            ExtractedMaterial(
                id="cv_unit_test",
                name="2x4 Lumber",
                quantity=10,
                unit="pieces",
                category="lumber",
                confidence=0.90,
                extracted_from="claude_vision"
            )
        ]

        matched = await bridge.process_extracted_materials(materials, "test_003")

        if matched:
            # Should have standardized unit
            assert "unit" in matched[0]
            assert matched[0]["unit"] in ["pieces", "linear_feet", "board_feet"]

    @pytest.mark.asyncio
    async def test_empty_materials_list(self, bridge):
        """Test: Handles empty materials list gracefully."""
        matched = await bridge.process_extracted_materials([], "test_004")

        assert matched == []

    @pytest.mark.asyncio
    async def test_preserve_specifications(self, bridge):
        """Test: Material specifications preserved through matching."""
        materials = [
            ExtractedMaterial(
                id="cv_spec_test",
                name="2x4 Stud",
                quantity=20,
                unit="pieces",
                category="lumber",
                confidence=0.92,
                extracted_from="claude_vision",
                specifications={"grade": "2", "species": "SPF", "length_ft": 8}
            )
        ]

        matched = await bridge.process_extracted_materials(materials, "test_005")

        if matched:
            assert "specifications" in matched[0]
            assert matched[0]["specifications"]["grade"] == "2"

    @pytest.mark.asyncio
    async def test_room_location_preserved(self, bridge):
        """Test: Room location preserved through matching."""
        materials = [
            ExtractedMaterial(
                id="cv_room_test",
                name="Drywall",
                quantity=10,
                unit="sheets",
                category="drywall",
                confidence=0.88,
                extracted_from="claude_vision",
                room_location="Kitchen"
            )
        ]

        matched = await bridge.process_extracted_materials(materials, "test_006")

        if matched:
            assert matched[0]["room_location"] == "Kitchen"


class TestMaterialMatchingValidator:
    """Test validation of matched materials."""

    def test_valid_matched_material(self):
        """Test: Valid matched material passes validation."""
        material = {
            "material_id": "lib_2x4_spf",
            "matched_name": "2x4 Stud - SPF",
            "quantity": 42,
            "unit": "pieces",
            "category": "lumber",
            "match_confidence": 0.92
        }

        errors = MaterialMatchingValidator.validate_matched_materials([material])

        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test: Missing fields caught."""
        material = {
            "material_id": "lib_2x4",
            "matched_name": "2x4 Stud"
            # Missing: quantity, unit, category
        }

        errors = MaterialMatchingValidator.validate_matched_materials([material])

        assert len(errors) > 0
        assert any("missing field" in e for e in errors)

    def test_invalid_quantity(self):
        """Test: Invalid quantities rejected."""
        material = {
            "material_id": "lib_test",
            "matched_name": "Test",
            "quantity": -5,  # Invalid
            "unit": "pieces",
            "category": "lumber",
            "match_confidence": 0.90
        }

        errors = MaterialMatchingValidator.validate_matched_materials([material])

        assert any("invalid quantity" in e for e in errors)

    def test_invalid_confidence(self):
        """Test: Confidence out of range caught."""
        material = {
            "material_id": "lib_test",
            "matched_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "category": "lumber",
            "match_confidence": 1.5  # Invalid (>1.0)
        }

        errors = MaterialMatchingValidator.validate_matched_materials([material])

        assert any("confidence out of range" in e for e in errors)

    def test_invalid_library_id_format(self):
        """Test: Library ID format validation."""
        material = {
            "material_id": "invalid_format",  # Should start with "lib_"
            "matched_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "category": "lumber",
            "match_confidence": 0.90
        }

        errors = MaterialMatchingValidator.validate_matched_materials([material])

        assert any("invalid library ID" in e for e in errors)


class TestDataContracts:
    """Test data contracts between Claude Vision and Material Matching."""

    def test_extracted_material_to_matched_contract(self):
        """Test: ExtractedMaterial → Matched Material schema."""
        extracted = ExtractedMaterial(
            id="test",
            name="Test Material",
            quantity=10,
            unit="pieces",
            category="lumber",
            confidence=0.90,
            extracted_from="claude_vision"
        )

        # Should have all required fields for matching
        assert extracted.name  # For fuzzy matching
        assert extracted.quantity > 0  # For quantity normalization
        assert extracted.unit  # For unit conversion
        assert extracted.category  # For category filtering
        assert 0 <= extracted.confidence <= 1  # For confidence calculation

    def test_matched_material_output_schema(self):
        """Test: Matched material output meets schema."""
        matched = {
            "material_id": "lib_2x4_spf",
            "original_name": "2x4 Stud - SPF - 8ft",
            "matched_name": "2x4 Stud - SPF - 8ft",
            "quantity": 42,
            "original_quantity": 42,
            "unit": "pieces",
            "original_unit": "pieces",
            "category": "lumber",
            "match_confidence": 0.92,
            "extracted_confidence": 0.94,
            "combined_confidence": 0.93
        }

        # Validate contract
        errors = MaterialMatchingValidator.validate_matched_materials([matched])
        assert len(errors) == 0

        # Should be ready for next agent (Pricing)
        assert matched["material_id"]  # For pricing lookup
        assert matched["quantity"] > 0  # For cost calculation
        assert matched["unit"]  # For unit-price conversion


class TestPerformance:
    """Test performance metrics."""

    @pytest.mark.asyncio
    async def test_batch_processing_latency(self):
        """Test: Batch processing meets latency targets."""
        import time

        bridge = ClaudeVisionMaterialMatchingBridge()

        materials = [
            ExtractedMaterial(
                id=f"perf_{i}",
                name=f"Material {i}",
                quantity=10,
                unit="pieces",
                category="lumber",
                confidence=0.90,
                extracted_from="claude_vision"
            )
            for i in range(50)  # 50 materials
        ]

        start = time.time()
        await bridge.process_extracted_materials(materials, "perf_test")
        elapsed = time.time() - start

        # Should process 50 materials in <1 second
        assert elapsed < 1.0, f"Processing took {elapsed:.2f}s, target <1.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
