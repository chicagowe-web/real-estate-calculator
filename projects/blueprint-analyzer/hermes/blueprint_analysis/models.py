"""
Shared data models for blueprint analysis pipeline.

These are the immutable Phase 1 contracts that all 9 agents implement against.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ExtractedMaterial:
    """Material extracted from blueprint by Claude Vision."""
    id: str
    name: str
    quantity: float
    unit: str
    category: str
    confidence: float
    extracted_from: str = "claude_vision"
    specifications: Optional[Dict[str, Any]] = None
    room_location: Optional[str] = None


@dataclass
class PreprocessedBlueprint:
    """Blueprint after preprocessing (upscaling, feature detection)."""
    file_hash: str
    preprocessed_image_path: str
    image_quality_score: float
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class MaterialPrice:
    """Pricing information for a material."""
    material_id: str
    product_name: str
    unit_price: float
    total_price: float
    source: str
    confidence: float
    region: str = "default"
    supplier: str = "unknown"


@dataclass
class LaborEstimate:
    """Labor cost estimate for a category."""
    category: str
    hours: float
    wage_rate: float
    total_labor_cost: float
    complexity_factor: str


@dataclass
class BlueprintAnalysisRequest:
    """User request to analyze a blueprint."""
    file_path: str
    project_name: str
    location_zip: Optional[str] = None
    blueprint_area_sqft: Optional[float] = None


@dataclass
class BlueprintAnalysisResponse:
    """Complete analysis response."""
    estimate_id: str
    status: str
    materials: List[Dict[str, Any]]
    pricing: List[Dict[str, Any]]
    labor: List[Dict[str, Any]]
    summary: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None


if __name__ == "__main__":
    print("✓ Models module ready")
