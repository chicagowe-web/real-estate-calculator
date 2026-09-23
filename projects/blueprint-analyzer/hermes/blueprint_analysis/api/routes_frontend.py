"""
Integration: API → Frontend (Agent 7).

Provides estimate data for React SPA with UI-optimized formatting.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class FrontendTransformer:
    """Transforms estimate data for React frontend."""

    @staticmethod
    async def transform_for_display(estimate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform estimate for frontend display.

        Adds:
        - UI flags for confidence levels
        - Chart data (by category, by room)
        - Material groupings for list display
        - Export options
        """
        return {
            "estimate_id": estimate.get("estimate_id"),
            "status": estimate.get("status"),
            "timestamp": estimate.get("timestamp"),
            "summary": FrontendTransformer._transform_summary(estimate),
            "materials_list": FrontendTransformer._transform_materials_list(
                estimate.get("materials", [])
            ),
            "pricing_breakdown": FrontendTransformer._transform_pricing_breakdown(
                estimate.get("pricing", [])
            ),
            "labor_breakdown": FrontendTransformer._transform_labor_breakdown(
                estimate.get("labor", [])
            ),
            "charts": FrontendTransformer._build_charts(estimate),
            "quality": FrontendTransformer._transform_quality(estimate),
            "metadata": estimate.get("metadata", {}),
            "actions": {
                "can_export": True,
                "export_formats": ["pdf", "csv", "json"],
                "can_print": True
            }
        }

    @staticmethod
    def _transform_summary(estimate: Dict) -> Dict[str, Any]:
        """Transform summary for display."""
        summary = estimate.get("summary", {})
        total = summary.get("total_estimated_cost", 0)
        contingency = summary.get("contingency_amount", 0)
        with_contingency = summary.get("estimated_total_with_contingency", 0)

        return {
            "material_total": {
                "value": summary.get("total_material_cost", 0),
                "formatted": f"${summary.get('total_material_cost', 0):,.2f}",
                "percentage": round(
                    (summary.get("total_material_cost", 0) / total * 100) if total > 0 else 0,
                    1
                )
            },
            "labor_total": {
                "value": summary.get("total_labor_cost", 0),
                "formatted": f"${summary.get('total_labor_cost', 0):,.2f}",
                "percentage": round(
                    (summary.get("total_labor_cost", 0) / total * 100) if total > 0 else 0,
                    1
                )
            },
            "subtotal": {
                "value": total,
                "formatted": f"${total:,.2f}"
            },
            "contingency": {
                "value": contingency,
                "formatted": f"${contingency:,.2f}",
                "percentage": 15
            },
            "total_with_contingency": {
                "value": with_contingency,
                "formatted": f"${with_contingency:,.2f}"
            },
            "confidence_score": {
                "value": summary.get("confidence_score", 0),
                "percentage": round(summary.get("confidence_score", 0) * 100, 1),
                "level": FrontendTransformer._confidence_level(
                    summary.get("confidence_score", 0)
                )
            }
        }

    @staticmethod
    def _transform_materials_list(materials: List[Dict]) -> List[Dict[str, Any]]:
        """Transform materials for list display."""
        return [
            {
                "id": m.get("material_id"),
                "name": m.get("matched_name", m.get("original_name", "Unknown")),
                "category": m.get("category", "other"),
                "quantity": m.get("quantity", 0),
                "unit": m.get("unit", "pieces"),
                "confidence": m.get("combined_confidence", 0.8),
                "confidence_level": FrontendTransformer._confidence_level(
                    m.get("combined_confidence", 0.8)
                ),
                "specifications": m.get("specifications", {}),
                "location": m.get("room_location")
            }
            for m in materials
        ]

    @staticmethod
    def _transform_pricing_breakdown(pricing: List[Dict]) -> Dict[str, List[Dict]]:
        """Group pricing by category for display."""
        by_category = {}

        for p in pricing:
            category = p.get("category", "other")
            if category not in by_category:
                by_category[category] = []

            by_category[category].append({
                "id": p.get("material_id"),
                "product": p.get("product_name", "Unknown"),
                "quantity": p.get("quantity", 0),
                "unit": p.get("unit"),
                "unit_price": {
                    "value": p.get("unit_price", 0),
                    "formatted": f"${p.get('unit_price', 0):.2f}"
                },
                "total": {
                    "value": p.get("total_price", 0),
                    "formatted": f"${p.get('total_price', 0):,.2f}"
                },
                "source": p.get("source", "unknown"),
                "confidence": p.get("confidence", 0.8),
                "supplier": p.get("supplier", "Unknown")
            })

        return by_category

    @staticmethod
    def _transform_labor_breakdown(labor: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Transform labor by trade category."""
        by_category = {}

        for l in labor:
            category = l.get("category", "other")
            by_category[category] = {
                "category": category,
                "hours": {
                    "value": l.get("hours", 0),
                    "formatted": f"{l.get('hours', 0):.1f}h"
                },
                "wage_rate": {
                    "value": l.get("wage_rate", 0),
                    "formatted": f"${l.get('wage_rate', 0):.2f}/hr"
                },
                "total_cost": {
                    "value": l.get("total_labor_cost", 0),
                    "formatted": f"${l.get('total_labor_cost', 0):,.2f}"
                },
                "complexity": l.get("complexity_factor", "moderate"),
                "materials_in_category": l.get("materials_in_category", 0)
            }

        return by_category

    @staticmethod
    def _build_charts(estimate: Dict) -> Dict[str, List[Dict]]:
        """Build chart data for UI visualizations."""
        summary = estimate.get("summary", {})

        return {
            "material_by_category": [
                {
                    "name": cat,
                    "value": cost,
                    "formatted": f"${cost:,.2f}",
                    "percentage": round(
                        (cost / summary.get("total_material_cost", 1) * 100)
                        if summary.get("total_material_cost", 0) > 0
                        else 0,
                        1
                    )
                }
                for cat, cost in summary.get("material_categories", {}).items()
            ],
            "labor_by_category": [
                {
                    "name": cat,
                    "value": cost,
                    "formatted": f"${cost:,.2f}",
                    "percentage": round(
                        (cost / summary.get("total_labor_cost", 1) * 100)
                        if summary.get("total_labor_cost", 0) > 0
                        else 0,
                        1
                    )
                }
                for cat, cost in summary.get("labor_by_category", {}).items()
            ],
            "cost_breakdown": [
                {
                    "name": "Materials",
                    "value": summary.get("total_material_cost", 0),
                    "formatted": f"${summary.get('total_material_cost', 0):,.2f}",
                    "percentage": round(
                        (summary.get("total_material_cost", 0) / summary.get("total_estimated_cost", 1) * 100)
                        if summary.get("total_estimated_cost", 0) > 0
                        else 0,
                        1
                    )
                },
                {
                    "name": "Labor",
                    "value": summary.get("total_labor_cost", 0),
                    "formatted": f"${summary.get('total_labor_cost', 0):,.2f}",
                    "percentage": round(
                        (summary.get("total_labor_cost", 0) / summary.get("total_estimated_cost", 1) * 100)
                        if summary.get("total_estimated_cost", 0) > 0
                        else 0,
                        1
                    )
                }
            ]
        }

    @staticmethod
    def _transform_quality(estimate: Dict) -> Dict[str, Any]:
        """Transform quality metrics for display."""
        metrics = estimate.get("quality_metrics", {})
        overall = metrics.get("overall_confidence", 0)

        return {
            "overall_confidence": {
                "value": overall,
                "percentage": round(overall * 100, 1),
                "level": FrontendTransformer._confidence_level(overall)
            },
            "material_confidence": {
                "value": metrics.get("material_confidence", 0),
                "percentage": round(metrics.get("material_confidence", 0) * 100, 1),
                "level": FrontendTransformer._confidence_level(
                    metrics.get("material_confidence", 0)
                )
            },
            "pricing_confidence": {
                "value": metrics.get("pricing_confidence", 0),
                "percentage": round(metrics.get("pricing_confidence", 0) * 100, 1),
                "level": FrontendTransformer._confidence_level(
                    metrics.get("pricing_confidence", 0)
                )
            },
            "labor_confidence": {
                "value": metrics.get("labor_confidence", 0),
                "percentage": round(metrics.get("labor_confidence", 0) * 100, 1),
                "level": FrontendTransformer._confidence_level(
                    metrics.get("labor_confidence", 0)
                )
            }
        }

    @staticmethod
    def _confidence_level(score: float) -> str:
        """Map confidence score to UI level."""
        if score >= 0.90:
            return "excellent"
        elif score >= 0.80:
            return "good"
        elif score >= 0.70:
            return "fair"
        else:
            return "needs_review"


class FrontendExporter:
    """Exports estimates in various formats."""

    @staticmethod
    async def export_estimate(
        estimate: Dict[str, Any],
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export estimate in specified format.

        Args:
            estimate: Aggregated estimate
            format: Export format (json, csv, pdf)

        Returns:
            Export result with content and metadata
        """
        logger.info(f"Exporting estimate {estimate.get('estimate_id')} as {format}")

        if format == "json":
            return await FrontendExporter._export_json(estimate)
        elif format == "csv":
            return await FrontendExporter._export_csv(estimate)
        elif format == "pdf":
            return await FrontendExporter._export_pdf(estimate)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    async def _export_json(estimate: Dict) -> Dict[str, Any]:
        """Export as JSON."""
        import json

        return {
            "format": "json",
            "filename": f"estimate_{estimate.get('estimate_id')}.json",
            "content": json.dumps(estimate, indent=2),
            "mime_type": "application/json"
        }

    @staticmethod
    async def _export_csv(estimate: Dict) -> Dict[str, Any]:
        """Export as CSV."""
        lines = [
            "Estimate Report",
            f"ID: {estimate.get('estimate_id')}",
            "",
            "SUMMARY",
            f"Materials Total,{estimate.get('summary', {}).get('total_material_cost', 0)}",
            f"Labor Total,{estimate.get('summary', {}).get('total_labor_cost', 0)}",
            f"Total Cost,{estimate.get('summary', {}).get('total_estimated_cost', 0)}",
            f"Confidence,{estimate.get('summary', {}).get('confidence_score', 0)}",
            "",
            "MATERIALS",
            "Material ID,Product,Quantity,Unit,Unit Price,Total Price,Source"
        ]

        for p in estimate.get("pricing", []):
            lines.append(
                f"{p.get('material_id')},{p.get('product_name')},"
                f"{p.get('quantity')},{p.get('unit')},"
                f"{p.get('unit_price')},{p.get('total_price')},{p.get('source')}"
            )

        lines.extend(["", "LABOR", "Category,Hours,Wage Rate,Total Cost,Complexity"])

        for l in estimate.get("labor", []):
            lines.append(
                f"{l.get('category')},{l.get('hours')},"
                f"{l.get('wage_rate')},{l.get('total_labor_cost')},"
                f"{l.get('complexity_factor')}"
            )

        return {
            "format": "csv",
            "filename": f"estimate_{estimate.get('estimate_id')}.csv",
            "content": "\n".join(lines),
            "mime_type": "text/csv"
        }

    @staticmethod
    async def _export_pdf(estimate: Dict) -> Dict[str, Any]:
        """Export as PDF (placeholder)."""
        # In real implementation, use ReportLab or similar
        return {
            "format": "pdf",
            "filename": f"estimate_{estimate.get('estimate_id')}.pdf",
            "content": b"PDF content would be generated here",
            "mime_type": "application/pdf"
        }


if __name__ == "__main__":
    print("✓ Frontend integration module ready")
