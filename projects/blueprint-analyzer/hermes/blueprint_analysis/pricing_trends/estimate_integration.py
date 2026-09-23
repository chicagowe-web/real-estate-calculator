"""
Integration: Pipeline → Pricing Trends (Agent 9).

Records pricing data from each estimate for quarterly trend analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PricingSnapshot:
    """Single pricing snapshot for trend tracking."""
    material_id: str
    material_name: str
    source: str
    unit_price: float
    quantity: float
    unit: str
    timestamp: str
    region: str
    estimate_id: str
    category: str
    supplier: Optional[str] = None
    confidence: float = 0.8


class PricingTrendsRecorder:
    """Records pricing data from estimates for trend analysis."""

    def __init__(self):
        self.snapshots_recorded = 0
        logger.info("PricingTrendsRecorder initialized")

    async def record_estimate_pricing(
        self,
        estimate_id: str,
        pricing_results: List[Dict[str, Any]],
        location_zip: str = None,
        blueprint_area_sqft: float = None
    ) -> Dict[str, Any]:
        """
        Record pricing snapshot from estimate for trend tracking.

        Args:
            estimate_id: ID of estimate
            pricing_results: Pricing results from Agent 5
            location_zip: Regional identifier (for regional trends)
            blueprint_area_sqft: Project area for normalization

        Returns:
            Recording summary with snapshot count
        """
        if not pricing_results:
            logger.warning(f"No pricing results to record for {estimate_id}")
            return {"recorded": 0, "estimate_id": estimate_id}

        logger.info(f"Recording pricing snapshots for {estimate_id} ({len(pricing_results)} items)")

        snapshots = []
        failed_records = []

        for price in pricing_results:
            try:
                snapshot = PricingSnapshot(
                    material_id=price.get("material_id", "unknown"),
                    material_name=price.get("product_name", "unknown"),
                    source=price.get("source", "unknown"),
                    unit_price=price.get("unit_price", 0),
                    quantity=price.get("quantity", 0),
                    unit=price.get("unit", "pieces"),
                    timestamp=datetime.now().isoformat(),
                    region=location_zip or "default",
                    estimate_id=estimate_id,
                    category=price.get("category", "other"),
                    supplier=price.get("supplier", None),
                    confidence=price.get("confidence", 0.8)
                )

                snapshots.append(snapshot)

            except Exception as e:
                logger.error(f"Failed to create snapshot for {price.get('material_id')}: {e}")
                failed_records.append(price.get("material_id", "unknown"))
                continue

        # Store snapshots in trends database
        try:
            stored_count = await self._store_snapshots(snapshots)
            logger.info(f"Stored {stored_count} pricing snapshots for {estimate_id}")

            return {
                "recorded": stored_count,
                "failed": len(failed_records),
                "estimate_id": estimate_id,
                "timestamp": datetime.now().isoformat(),
                "region": location_zip or "default"
            }

        except Exception as e:
            logger.error(f"Failed to store pricing snapshots: {e}")
            return {
                "recorded": 0,
                "failed": len(pricing_results),
                "estimate_id": estimate_id,
                "error": str(e)
            }

    async def _store_snapshots(self, snapshots: List[PricingSnapshot]) -> int:
        """
        Store pricing snapshots in database.

        In real implementation, this would INSERT into daily_prices table.
        For now, logs snapshots (ready for integration with actual DB).
        """
        if not snapshots:
            return 0

        # Log snapshot data (in production, this would be database INSERT)
        logger.debug(f"Storing {len(snapshots)} snapshots:")
        for snapshot in snapshots:
            logger.debug(
                f"  {snapshot.material_id}: ${snapshot.unit_price} "
                f"({snapshot.source}) @ {snapshot.timestamp}"
            )

        # Return count of stored records
        return len(snapshots)

    async def get_price_history(
        self,
        material_id: str,
        days: int = 90,
        region: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve price history for trend analysis.

        Args:
            material_id: Material to analyze
            days: Number of days of history to retrieve
            region: Optional region filter

        Returns:
            List of historical price records
        """
        # In real implementation, would query database
        logger.info(f"Retrieving {days}-day price history for {material_id}")

        return []  # Placeholder for DB query

    async def get_price_trends(
        self,
        category: str = None,
        days: int = 90,
        region: str = None
    ) -> Dict[str, Any]:
        """
        Analyze price trends for category.

        Args:
            category: Material category (lumber, electrical, etc.)
            days: Analysis period in days
            region: Optional region filter

        Returns:
            Trend analysis with price movements
        """
        logger.info(f"Analyzing price trends for {category or 'all'} ({days} days)")

        return {
            "category": category,
            "period_days": days,
            "region": region or "all",
            "trend_direction": "stable",  # Would be calculated from data
            "average_price_change": 0.0,
            "items_tracked": 0,
            "samples": []
        }


class TrendAnalyzer:
    """Analyzes pricing trends over time."""

    @staticmethod
    def calculate_trend(prices: List[Dict]) -> Dict[str, Any]:
        """
        Calculate trend from price history.

        Args:
            prices: Historical price records

        Returns:
            Trend analysis
        """
        if len(prices) < 2:
            return {
                "direction": "insufficient_data",
                "percentage_change": 0.0,
                "average_price": prices[0].get("unit_price", 0) if prices else 0
            }

        # Sort by date
        sorted_prices = sorted(prices, key=lambda x: x.get("timestamp", ""))

        # Calculate change
        first_price = sorted_prices[0].get("unit_price", 0)
        last_price = sorted_prices[-1].get("unit_price", 0)

        if first_price == 0:
            percentage_change = 0
        else:
            percentage_change = ((last_price - first_price) / first_price) * 100

        # Determine direction
        if percentage_change > 2:
            direction = "increasing"
        elif percentage_change < -2:
            direction = "decreasing"
        else:
            direction = "stable"

        average = sum(p.get("unit_price", 0) for p in sorted_prices) / len(sorted_prices)

        return {
            "direction": direction,
            "percentage_change": round(percentage_change, 2),
            "average_price": round(average, 2),
            "first_price": first_price,
            "last_price": last_price,
            "sample_count": len(prices)
        }

    @staticmethod
    def calculate_quarterly_summary(estimates: List[Dict]) -> Dict[str, Any]:
        """
        Summarize quarterly pricing trends.

        Args:
            estimates: List of estimates from the quarter

        Returns:
            Quarterly summary
        """
        if not estimates:
            return {
                "period": "Q current",
                "total_estimates": 0,
                "avg_material_cost": 0,
                "avg_labor_cost": 0,
                "total_recorded_prices": 0
            }

        # Aggregate statistics
        total_material = sum(e.get("summary", {}).get("total_material_cost", 0) for e in estimates)
        total_labor = sum(e.get("summary", {}).get("total_labor_cost", 0) for e in estimates)
        avg_material = total_material / len(estimates) if estimates else 0
        avg_labor = total_labor / len(estimates) if estimates else 0

        return {
            "period": "Q current",
            "total_estimates": len(estimates),
            "avg_material_cost": round(avg_material, 2),
            "avg_labor_cost": round(avg_labor, 2),
            "total_material_cost": round(total_material, 2),
            "total_labor_cost": round(total_labor, 2),
            "categories_tracked": len(set(
                p.get("category") for e in estimates
                for p in e.get("pricing", [])
            ))
        }


if __name__ == "__main__":
    print("✓ Pricing trends module ready")
