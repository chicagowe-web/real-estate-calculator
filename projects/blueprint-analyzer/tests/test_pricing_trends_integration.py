"""
Tests for Pricing Trends integration (pipeline → pricing trends recorder).
"""

import pytest
from typing import List, Dict, Any

from hermes.blueprint_analysis.pricing_trends.estimate_integration import (
    PricingTrendsRecorder,
    PricingSnapshot,
    TrendAnalyzer,
)


class TestPricingTrendsRecorder:
    """Test pricing snapshot recording."""

    @pytest.fixture
    def recorder(self):
        """Initialize recorder for tests."""
        return PricingTrendsRecorder()

    @pytest.fixture
    def sample_pricing_results(self) -> List[Dict]:
        """Sample pricing results to record."""
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
                "category": "framing",
                "supplier": "Home Depot Inc."
            },
            {
                "material_id": "lib_drywall",
                "product_name": "Drywall Sheet - 5/8\"",
                "quantity": 15,
                "unit": "sheets",
                "unit_price": 15.00,
                "total_price": 225.00,
                "source": "lowes",
                "confidence": 0.88,
                "category": "drywall",
                "supplier": "Lowe's"
            }
        ]

    @pytest.mark.asyncio
    async def test_record_pricing_success(self, recorder, sample_pricing_results):
        """Test: Pricing snapshots recorded successfully."""
        result = await recorder.record_estimate_pricing(
            estimate_id="est_001",
            pricing_results=sample_pricing_results,
            location_zip="60601"
        )

        assert result["recorded"] > 0
        assert result["estimate_id"] == "est_001"
        assert result["region"] == "60601"

    @pytest.mark.asyncio
    async def test_empty_pricing_results(self, recorder):
        """Test: Handles empty pricing results."""
        result = await recorder.record_estimate_pricing(
            estimate_id="est_002",
            pricing_results=[]
        )

        assert result["recorded"] == 0

    @pytest.mark.asyncio
    async def test_snapshot_metadata(self, recorder, sample_pricing_results):
        """Test: Snapshot captures required metadata."""
        result = await recorder.record_estimate_pricing(
            estimate_id="est_003",
            pricing_results=sample_pricing_results,
            location_zip="90210"
        )

        assert "timestamp" in result
        assert "region" in result
        assert result["region"] == "90210"

    @pytest.mark.asyncio
    async def test_default_region(self, recorder, sample_pricing_results):
        """Test: Uses default region if not specified."""
        result = await recorder.record_estimate_pricing(
            estimate_id="est_004",
            pricing_results=sample_pricing_results
        )

        assert result["region"] == "default"

    @pytest.mark.asyncio
    async def test_multiple_sources_tracked(self, recorder):
        """Test: Multiple price sources tracked."""
        pricing = [
            {
                "material_id": "lib_test1",
                "product_name": "Test 1",
                "quantity": 10,
                "unit": "pieces",
                "unit_price": 5.00,
                "total_price": 50.00,
                "source": "home_depot",
                "confidence": 0.92,
                "category": "lumber"
            },
            {
                "material_id": "lib_test2",
                "product_name": "Test 2",
                "quantity": 10,
                "unit": "pieces",
                "unit_price": 4.99,
                "total_price": 49.90,
                "source": "lowes",
                "confidence": 0.88,
                "category": "lumber"
            }
        ]

        result = await recorder.record_estimate_pricing(
            estimate_id="est_005",
            pricing_results=pricing
        )

        assert result["recorded"] == 2


class TestPricingSnapshot:
    """Test PricingSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test: Snapshot created correctly."""
        snapshot = PricingSnapshot(
            material_id="lib_test",
            material_name="Test Material",
            source="home_depot",
            unit_price=5.00,
            quantity=10,
            unit="pieces",
            timestamp="2026-09-23T10:00:00",
            region="midwest",
            estimate_id="est_001",
            category="lumber"
        )

        assert snapshot.material_id == "lib_test"
        assert snapshot.unit_price == 5.00
        assert snapshot.region == "midwest"


class TestTrendAnalyzer:
    """Test trend analysis calculations."""

    def test_increasing_trend(self):
        """Test: Increasing trend detected."""
        prices = [
            {"unit_price": 4.00, "timestamp": "2026-09-01"},
            {"unit_price": 4.50, "timestamp": "2026-09-15"},
            {"unit_price": 5.00, "timestamp": "2026-09-30"}
        ]

        trend = TrendAnalyzer.calculate_trend(prices)

        assert trend["direction"] == "increasing"
        assert trend["percentage_change"] > 0
        assert trend["sample_count"] == 3

    def test_decreasing_trend(self):
        """Test: Decreasing trend detected."""
        prices = [
            {"unit_price": 5.00, "timestamp": "2026-09-01"},
            {"unit_price": 4.50, "timestamp": "2026-09-15"},
            {"unit_price": 4.00, "timestamp": "2026-09-30"}
        ]

        trend = TrendAnalyzer.calculate_trend(prices)

        assert trend["direction"] == "decreasing"
        assert trend["percentage_change"] < 0

    def test_stable_trend(self):
        """Test: Stable trend detected."""
        prices = [
            {"unit_price": 4.50, "timestamp": "2026-09-01"},
            {"unit_price": 4.52, "timestamp": "2026-09-15"},
            {"unit_price": 4.49, "timestamp": "2026-09-30"}
        ]

        trend = TrendAnalyzer.calculate_trend(prices)

        assert trend["direction"] == "stable"
        assert abs(trend["percentage_change"]) < 2

    def test_insufficient_data(self):
        """Test: Handles insufficient data."""
        prices = [{"unit_price": 4.50, "timestamp": "2026-09-01"}]

        trend = TrendAnalyzer.calculate_trend(prices)

        assert trend["direction"] == "insufficient_data"
        assert trend["percentage_change"] == 0

    def test_average_price_calculation(self):
        """Test: Average price calculated."""
        prices = [
            {"unit_price": 2.00, "timestamp": "2026-09-01"},
            {"unit_price": 4.00, "timestamp": "2026-09-15"},
            {"unit_price": 6.00, "timestamp": "2026-09-30"}
        ]

        trend = TrendAnalyzer.calculate_trend(prices)

        assert trend["average_price"] == 4.00

    def test_quarterly_summary(self):
        """Test: Quarterly summary calculated."""
        estimates = [
            {
                "summary": {
                    "total_material_cost": 500.00,
                    "total_labor_cost": 200.00
                },
                "pricing": [{"category": "lumber"}]
            },
            {
                "summary": {
                    "total_material_cost": 600.00,
                    "total_labor_cost": 300.00
                },
                "pricing": [{"category": "electrical"}]
            }
        ]

        summary = TrendAnalyzer.calculate_quarterly_summary(estimates)

        assert summary["total_estimates"] == 2
        assert summary["avg_material_cost"] == 550.00
        assert summary["avg_labor_cost"] == 250.00
        assert summary["total_material_cost"] == 1100.00

    def test_quarterly_summary_empty(self):
        """Test: Quarterly summary handles empty list."""
        summary = TrendAnalyzer.calculate_quarterly_summary([])

        assert summary["total_estimates"] == 0
        assert summary["avg_material_cost"] == 0


class TestPriceHistory:
    """Test price history retrieval."""

    @pytest.mark.asyncio
    async def test_get_price_history(self):
        """Test: Price history retrieval (placeholder)."""
        recorder = PricingTrendsRecorder()

        history = await recorder.get_price_history(
            material_id="lib_test",
            days=90
        )

        # Placeholder returns empty list
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_price_trends(self):
        """Test: Price trends retrieval (placeholder)."""
        recorder = PricingTrendsRecorder()

        trends = await recorder.get_price_trends(
            category="lumber",
            days=90
        )

        assert "category" in trends
        assert "period_days" in trends
        assert trends["category"] == "lumber"


class TestDataContracts:
    """Test data contracts for pricing trends."""

    def test_pricing_result_to_snapshot_contract(self):
        """Test: Pricing result has all fields for snapshot."""
        pricing = {
            "material_id": "lib_test",
            "product_name": "Test",
            "quantity": 10,
            "unit": "pieces",
            "unit_price": 5.00,
            "source": "home_depot",
            "confidence": 0.90,
            "category": "lumber",
            "supplier": "Home Depot"
        }

        # Should have all fields for snapshot creation
        assert pricing["material_id"]
        assert pricing["product_name"]
        assert pricing["unit_price"] >= 0
        assert pricing["source"]
        assert pricing["category"]

    def test_snapshot_trend_analysis_contract(self):
        """Test: Snapshots ready for trend analysis."""
        snapshots = [
            {
                "material_id": "lib_test",
                "unit_price": 5.00,
                "timestamp": "2026-09-01",
                "region": "midwest",
                "category": "lumber"
            },
            {
                "material_id": "lib_test",
                "unit_price": 5.10,
                "timestamp": "2026-09-15",
                "region": "midwest",
                "category": "lumber"
            }
        ]

        # Should have all fields for trend analysis
        for snapshot in snapshots:
            assert "unit_price" in snapshot
            assert "timestamp" in snapshot
            assert "material_id" in snapshot


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
