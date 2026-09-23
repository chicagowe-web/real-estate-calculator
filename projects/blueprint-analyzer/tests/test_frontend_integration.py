"""
Tests for Frontend integration (API → Frontend).
"""

import pytest
from typing import Dict, Any

from hermes.blueprint_analysis.api.routes_frontend import (
    FrontendTransformer,
    FrontendExporter,
    ExportFormat,
)


class TestFrontendTransformer:
    """Test transforming estimates for frontend display."""

    @pytest.fixture
    def sample_estimate(self) -> Dict[str, Any]:
        """Sample complete estimate."""
        return {
            "estimate_id": "est_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [
                {
                    "material_id": "lib_2x4",
                    "matched_name": "2x4 Stud - SPF",
                    "quantity": 42,
                    "unit": "pieces",
                    "category": "framing",
                    "combined_confidence": 0.92,
                    "specifications": {"grade": "2"}
                }
            ],
            "pricing": [
                {
                    "material_id": "lib_2x4",
                    "product_name": "2x4 Stud - SPF",
                    "quantity": 42,
                    "unit": "pieces",
                    "unit_price": 4.49,
                    "total_price": 188.58,
                    "source": "home_depot",
                    "confidence": 0.92,
                    "category": "framing"
                }
            ],
            "labor": [
                {
                    "category": "framing",
                    "hours": 3.6,
                    "wage_rate": 45.00,
                    "total_labor_cost": 162.00,
                    "complexity_factor": "moderate",
                    "materials_in_category": 1
                }
            ],
            "summary": {
                "total_material_cost": 188.58,
                "total_labor_cost": 162.00,
                "total_estimated_cost": 350.58,
                "confidence_score": 0.92,
                "material_categories": {"framing": 188.58},
                "labor_by_category": {"framing": 162.00},
                "contingency_amount": 52.59,
                "estimated_total_with_contingency": 403.17
            },
            "quality_metrics": {
                "material_confidence": 0.92,
                "pricing_confidence": 0.92,
                "labor_confidence": 0.95,
                "overall_confidence": 0.93
            },
            "metadata": {
                "square_footage": 500.0,
                "location": "Kitchen"
            }
        }

    @pytest.mark.asyncio
    async def test_transform_for_display(self, sample_estimate):
        """Test: Transform estimate for display."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)

        assert result["estimate_id"] == "est_001"
        assert result["status"] == "completed"
        assert "summary" in result
        assert "materials_list" in result
        assert "pricing_breakdown" in result
        assert "labor_breakdown" in result
        assert "charts" in result
        assert "quality" in result

    @pytest.mark.asyncio
    async def test_summary_transformation(self, sample_estimate):
        """Test: Summary transformed with formatted values."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        summary = result["summary"]

        assert "material_total" in summary
        assert "labor_total" in summary
        assert "subtotal" in summary
        assert "contingency" in summary
        assert "total_with_contingency" in summary

        # Should have both numeric and formatted values
        assert "value" in summary["subtotal"]
        assert "formatted" in summary["subtotal"]
        assert "$" in summary["subtotal"]["formatted"]

    @pytest.mark.asyncio
    async def test_materials_list_transformation(self, sample_estimate):
        """Test: Materials list transformed for display."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        materials = result["materials_list"]

        assert len(materials) > 0
        mat = materials[0]

        assert "id" in mat
        assert "name" in mat
        assert "quantity" in mat
        assert "confidence" in mat
        assert "confidence_level" in mat

    @pytest.mark.asyncio
    async def test_pricing_breakdown(self, sample_estimate):
        """Test: Pricing grouped by category."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        pricing = result["pricing_breakdown"]

        assert "framing" in pricing
        assert len(pricing["framing"]) > 0

        item = pricing["framing"][0]
        assert "product" in item
        assert "quantity" in item
        assert "unit_price" in item
        assert "total" in item
        assert "formatted" in item["unit_price"]

    @pytest.mark.asyncio
    async def test_labor_breakdown(self, sample_estimate):
        """Test: Labor grouped by category."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        labor = result["labor_breakdown"]

        assert "framing" in labor
        labor_item = labor["framing"]

        assert "hours" in labor_item
        assert "wage_rate" in labor_item
        assert "total_cost" in labor_item
        assert "complexity" in labor_item

    @pytest.mark.asyncio
    async def test_chart_data_generation(self, sample_estimate):
        """Test: Chart data generated for UI."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        charts = result["charts"]

        assert "material_by_category" in charts
        assert "labor_by_category" in charts
        assert "cost_breakdown" in charts

        # Cost breakdown should have materials and labor
        cost_breakdown = charts["cost_breakdown"]
        assert len(cost_breakdown) == 2
        assert cost_breakdown[0]["name"] == "Materials"
        assert cost_breakdown[1]["name"] == "Labor"

    @pytest.mark.asyncio
    async def test_quality_metrics_transformation(self, sample_estimate):
        """Test: Quality metrics transformed."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        quality = result["quality"]

        assert "overall_confidence" in quality
        assert "material_confidence" in quality

        overall = quality["overall_confidence"]
        assert "value" in overall
        assert "percentage" in overall
        assert "level" in overall
        assert overall["level"] == "excellent"

    @pytest.mark.asyncio
    async def test_confidence_levels(self, sample_estimate):
        """Test: Confidence levels mapped correctly."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)
        quality = result["quality"]

        overall = quality["overall_confidence"]
        assert overall["level"] in ["excellent", "good", "fair", "needs_review"]

    @pytest.mark.asyncio
    async def test_formatting_consistency(self, sample_estimate):
        """Test: All currency values formatted consistently."""
        result = await FrontendTransformer.transform_for_display(sample_estimate)

        summary = result["summary"]
        assert "$" in summary["subtotal"]["formatted"]
        assert "$" in summary["material_total"]["formatted"]

        charts = result["charts"]
        for item in charts["cost_breakdown"]:
            assert "$" in item["formatted"]

    @pytest.mark.asyncio
    async def test_empty_estimate(self):
        """Test: Handles empty estimate gracefully."""
        empty_estimate = {
            "estimate_id": "empty_001",
            "status": "completed",
            "timestamp": "2026-09-23T10:00:00",
            "materials": [],
            "pricing": [],
            "labor": [],
            "summary": {
                "total_material_cost": 0,
                "total_labor_cost": 0,
                "total_estimated_cost": 0,
                "confidence_score": 0,
                "material_categories": {},
                "labor_by_category": {}
            },
            "quality_metrics": {}
        }

        result = await FrontendTransformer.transform_for_display(empty_estimate)

        assert result["estimate_id"] == "empty_001"
        assert len(result["materials_list"]) == 0
        assert result["summary"]["subtotal"]["value"] == 0


class TestFrontendExporter:
    """Test exporting estimates in various formats."""

    @pytest.fixture
    def sample_estimate(self) -> Dict[str, Any]:
        """Sample estimate for export."""
        return {
            "estimate_id": "est_export_001",
            "materials": [
                {
                    "material_id": "lib_test",
                    "product_name": "Test Material",
                    "quantity": 10,
                    "unit": "pieces",
                    "unit_price": 5.00,
                    "total_price": 50.00,
                    "source": "home_depot"
                }
            ],
            "pricing": [
                {
                    "material_id": "lib_test",
                    "product_name": "Test Material",
                    "quantity": 10,
                    "unit": "pieces",
                    "unit_price": 5.00,
                    "total_price": 50.00,
                    "source": "home_depot"
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
                "confidence_score": 0.90
            }
        }

    @pytest.mark.asyncio
    async def test_export_json(self, sample_estimate):
        """Test: Export as JSON."""
        result = await FrontendExporter.export_estimate(sample_estimate, "json")

        assert result["format"] == "json"
        assert "estimate_" in result["filename"] and ".json" in result["filename"]
        assert ".json" in result["filename"]
        assert result["mime_type"] == "application/json"
        assert "estimate_id" in result["content"]

    @pytest.mark.asyncio
    async def test_export_csv(self, sample_estimate):
        """Test: Export as CSV."""
        result = await FrontendExporter.export_estimate(sample_estimate, "csv")

        assert result["format"] == "csv"
        assert ".csv" in result["filename"]
        assert result["mime_type"] == "text/csv"
        assert "SUMMARY" in result["content"]
        assert "MATERIALS" in result["content"]
        assert "LABOR" in result["content"]

    @pytest.mark.asyncio
    async def test_export_pdf(self, sample_estimate):
        """Test: Export as PDF (placeholder)."""
        result = await FrontendExporter.export_estimate(sample_estimate, "pdf")

        assert result["format"] == "pdf"
        assert ".pdf" in result["filename"]
        assert result["mime_type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_invalid_export_format(self, sample_estimate):
        """Test: Invalid format rejected."""
        with pytest.raises(ValueError):
            await FrontendExporter.export_estimate(sample_estimate, "invalid")


class TestExportFormat:
    """Test export format enumeration."""

    def test_export_formats_defined(self):
        """Test: Standard formats defined."""
        assert hasattr(ExportFormat, "JSON")
        assert hasattr(ExportFormat, "CSV")
        assert hasattr(ExportFormat, "PDF")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
