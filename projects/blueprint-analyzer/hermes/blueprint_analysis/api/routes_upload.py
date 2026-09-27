"""
Blueprint Upload Routes - Task 3 Integration
Handles file uploads and runs Claude Vision extraction pipeline.

Endpoint: POST /api/v1/blueprints/upload
Returns: Estimate with extracted materials, ready for review
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from .upload_handler import BlueprintUploadHandler


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])

# Initialize upload handler
upload_handler = BlueprintUploadHandler()


# ============================================================================
# Request/Response Models
# ============================================================================

class UploadRequest(BaseModel):
    """File upload request model."""
    project_name: str
    location_zip: Optional[str] = None
    auto_extract: bool = True


class UploadResponse(BaseModel):
    """File upload response model."""
    estimate_id: str
    status: str
    filename: str
    project_name: str
    message: str
    materials_extracted: Optional[int] = None
    extraction_confidence: Optional[float] = None


class UploadStatusResponse(BaseModel):
    """Upload status response model."""
    estimate_id: str
    filename: str
    project_name: str
    status: str
    created_at: str
    materials_extracted: int
    avg_confidence: float


# ============================================================================
# Routes
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    location_zip: Optional[str] = Form(None),
    auto_extract: bool = Form(True)
) -> UploadResponse:
    """
    Upload a blueprint PDF and optionally run Claude Vision extraction.

    Parameters:
    - file: PDF blueprint file (required)
    - project_name: Name of the construction project (required)
    - location_zip: ZIP code for pricing context (optional)
    - auto_extract: Automatically run Claude Vision extraction (default: true)

    Returns:
    - estimate_id: Unique identifier for this blueprint estimate
    - status: "uploaded" | "extracted" | "error"
    - materials_extracted: Number of materials extracted (if auto_extract=true)
    - extraction_confidence: Average confidence score (if auto_extract=true)

    Example Response:
    ```json
    {
      "estimate_id": "est_abc123def456",
      "status": "extracted",
      "filename": "office_renovation.pdf",
      "project_name": "Downtown Office Renovation - 2nd Floor",
      "message": "Blueprint uploaded and analyzed successfully",
      "materials_extracted": 15,
      "extraction_confidence": 0.845
    }
    ```
    """
    try:
        logger.info(f"Received upload request: {file.filename} for project '{project_name}'")

        # Handle upload
        result = await upload_handler.handle_upload(
            file=file,
            project_name=project_name,
            location_zip=location_zip,
            auto_extract=auto_extract
        )

        logger.info(f"Upload successful: {result['estimate_id']}")

        return UploadResponse(
            estimate_id=result["estimate_id"],
            status=result["status"],
            filename=result["filename"],
            project_name=result["project_name"],
            message=result["message"],
            materials_extracted=result.get("materials_extracted"),
            extraction_confidence=result.get("extraction_confidence")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/upload/{estimate_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(estimate_id: str) -> UploadStatusResponse:
    """
    Get the status of an uploaded blueprint.

    Parameters:
    - estimate_id: Unique identifier of the estimate

    Returns:
    - status: Current status of the estimate
    - materials_extracted: Number of materials extracted
    - avg_confidence: Average confidence score of extractions

    Example Response:
    ```json
    {
      "estimate_id": "est_abc123def456",
      "filename": "office_renovation.pdf",
      "project_name": "Downtown Office Renovation - 2nd Floor",
      "status": "pending_review",
      "created_at": "2026-09-27T12:00:00.000000",
      "materials_extracted": 15,
      "avg_confidence": 0.845
    }
    ```
    """
    try:
        status = upload_handler.get_upload_status(estimate_id)
        return UploadStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {estimate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Integration with Existing API
# ============================================================================

@router.get("/recent")
async def get_recent_uploads(limit: int = 10):
    """
    Get recently uploaded blueprints (for dashboard sidebar).

    Parameters:
    - limit: Maximum number of recent uploads to return (default: 10)

    Returns:
    List of recent estimate objects with materials count and status.
    """
    import sqlite3
    from pathlib import Path
    import json

    db_path = Path("/tmp/blueprint_reviews.db")
    if not db_path.exists():
        return {"uploads": []}

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    try:
        c.execute("""
            SELECT id, filename, project_name, status, created_at, raw_extraction
            FROM estimates
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        uploads = []
        for row in c.fetchall():
            raw_extraction = json.loads(row[5]) if row[5] else []
            uploads.append({
                "estimate_id": row[0],
                "filename": row[1],
                "project_name": row[2],
                "status": row[3],
                "created_at": row[4],
                "materials_count": len(raw_extraction),
                "avg_confidence": (
                    sum(m.get("confidence", 0) for m in raw_extraction) / len(raw_extraction)
                    if raw_extraction else 0
                )
            })

        return {"uploads": uploads}

    finally:
        conn.close()


# ============================================================================
# Export Functions (Integration with Frontend)
# ============================================================================

@router.get("/estimate/{estimate_id}/materials")
async def get_estimate_materials(estimate_id: str):
    """
    Get materials extracted from a blueprint (for dashboard display).

    Returns materials list with confidence scoring and edit status.
    """
    import sqlite3
    from pathlib import Path
    import json

    db_path = Path("/tmp/blueprint_reviews.db")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    try:
        c.execute("""
            SELECT raw_extraction
            FROM estimates
            WHERE id = ?
        """, (estimate_id,))

        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Estimate not found")

        materials = json.loads(row[0]) if row[0] else []

        # Transform for UI
        materials_ui = []
        for mat in materials:
            confidence = mat.get("confidence", 0)

            # Determine confidence level for UI badge
            if confidence >= 0.85:
                confidence_level = "high"
                badge_color = "green"
            elif confidence >= 0.70:
                confidence_level = "medium"
                badge_color = "yellow"
            else:
                confidence_level = "low"
                badge_color = "red"

            materials_ui.append({
                "id": mat.get("id"),
                "name": mat.get("name"),
                "quantity": mat.get("quantity"),
                "unit": mat.get("unit"),
                "category": mat.get("category"),
                "confidence": confidence,
                "confidence_level": confidence_level,
                "badge_color": badge_color,
                "specifications": mat.get("specifications", {}),
                "room_location": mat.get("room_location"),
                "editable": True,
                "approved": False
            })

        return {
            "estimate_id": estimate_id,
            "materials": materials_ui,
            "summary": {
                "total": len(materials_ui),
                "high_confidence": sum(1 for m in materials_ui if m["confidence_level"] == "high"),
                "medium_confidence": sum(1 for m in materials_ui if m["confidence_level"] == "medium"),
                "low_confidence": sum(1 for m in materials_ui if m["confidence_level"] == "low")
            }
        }

    finally:
        conn.close()


# ============================================================================
# Testing Endpoint
# ============================================================================

@router.post("/test/upload")
async def test_upload():
    """
    Test endpoint to verify upload handler is working.

    Returns a mock upload response for testing without a real file.
    """
    return {
        "status": "ok",
        "message": "Upload handler is configured and ready",
        "endpoints": [
            "POST /api/v1/blueprints/upload - Upload a blueprint",
            "GET /api/v1/blueprints/upload/{estimate_id}/status - Get upload status",
            "GET /api/v1/blueprints/recent - Get recent uploads",
            "GET /api/v1/blueprints/estimate/{estimate_id}/materials - Get extracted materials"
        ]
    }


if __name__ == "__main__":
    print("✓ Upload routes module ready")
