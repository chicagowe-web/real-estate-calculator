"""
Blueprint Upload Handler - Task 3
Integrates Claude Vision extraction with dashboard workflow.

Flow: Upload PDF → Preprocess → Extract with Claude Vision → Store in DB → Return estimate ID
"""

import json
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import base64
import os

from fastapi import HTTPException, UploadFile
import sqlite3

from ..claude_vision.integration import ClaudeVisionIntegration, ClaudeVisionConfig
from ..models import ExtractedMaterial


logger = logging.getLogger(__name__)


class BlueprintUploadHandler:
    """Handle blueprint uploads and run Claude Vision extraction pipeline."""

    def __init__(self, db_path: str = "/tmp/blueprint_reviews.db"):
        self.db_path = db_path
        self.upload_dir = Path("/tmp/blueprint_uploads")
        self.upload_dir.mkdir(exist_ok=True)

        # Initialize Claude Vision integration
        self.vision = ClaudeVisionIntegration(
            config=ClaudeVisionConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048
            )
        )

    async def handle_upload(
        self,
        file: UploadFile,
        project_name: str,
        location_zip: Optional[str] = None,
        auto_extract: bool = True
    ) -> Dict[str, Any]:
        """
        Handle blueprint upload and optionally run extraction.

        Args:
            file: Uploaded PDF file
            project_name: Name of the project
            location_zip: ZIP code for pricing context (optional)
            auto_extract: Whether to immediately run Claude Vision extraction

        Returns:
            {
                "estimate_id": "est_...",
                "status": "uploaded|extracting|extracted",
                "filename": "...",
                "project_name": "...",
                "message": "..."
            }
        """
        try:
            estimate_id = f"est_{uuid.uuid4().hex[:12]}"
            filename = file.filename or "blueprint.pdf"

            # Validate file
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files supported")

            file_size = 0
            file_path = self.upload_dir / f"{estimate_id}_{filename}"

            # Save file
            logger.info(f"Saving uploaded file: {filename} (estimate_id={estimate_id})")
            content = await file.read()
            file_size = len(content)

            with open(file_path, "wb") as f:
                f.write(content)

            # Create estimate record in DB
            self._create_estimate_record(
                estimate_id=estimate_id,
                filename=filename,
                project_name=project_name,
                location_zip=location_zip or "",
                file_path=str(file_path),
                file_size=file_size
            )

            logger.info(f"Created estimate record: {estimate_id}")

            result = {
                "estimate_id": estimate_id,
                "status": "uploaded",
                "filename": filename,
                "project_name": project_name,
                "location_zip": location_zip,
                "file_size": file_size,
                "message": f"Blueprint uploaded successfully"
            }

            # Run Claude Vision extraction if requested
            if auto_extract:
                logger.info(f"Starting Claude Vision extraction for {estimate_id}...")
                extraction_result = await self._extract_with_claude_vision(
                    estimate_id=estimate_id,
                    file_path=str(file_path),
                    project_name=project_name
                )

                result.update({
                    "status": "extracted",
                    "extraction_status": extraction_result.get("status"),
                    "materials_extracted": extraction_result.get("materials_count", 0),
                    "extraction_confidence": extraction_result.get("avg_confidence", 0)
                })

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def _extract_with_claude_vision(
        self,
        estimate_id: str,
        file_path: str,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run Claude Vision extraction on uploaded blueprint.

        Returns:
            {
                "status": "success|error",
                "materials_count": N,
                "avg_confidence": 0.85,
                "materials": [...]
            }
        """
        try:
            logger.info(f"Extracting materials from {file_path}...")

            # Read PDF file
            with open(file_path, "rb") as f:
                pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Call Claude Vision API
            materials = self.vision.extract_materials(
                pdf_data=pdf_data,
                blueprint_id=estimate_id
            )

            logger.info(f"Extracted {len(materials)} materials for {estimate_id}")

            # Calculate average confidence
            avg_confidence = (
                sum(m.confidence for m in materials) / len(materials)
                if materials else 0
            )

            # Store extracted materials in DB
            self._save_extraction_results(
                estimate_id=estimate_id,
                materials=materials,
                avg_confidence=avg_confidence
            )

            return {
                "status": "success",
                "materials_count": len(materials),
                "avg_confidence": avg_confidence,
                "materials": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "quantity": m.quantity,
                        "unit": m.unit,
                        "category": m.category,
                        "confidence": m.confidence
                    }
                    for m in materials
                ]
            }

        except Exception as e:
            logger.error(f"Claude Vision extraction failed: {e}")
            return {
                "status": "error",
                "materials_count": 0,
                "avg_confidence": 0,
                "error": str(e)
            }

    def _create_estimate_record(
        self,
        estimate_id: str,
        filename: str,
        project_name: str,
        location_zip: str,
        file_path: str,
        file_size: int
    ):
        """Create an estimate record in the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute("""
                CREATE TABLE IF NOT EXISTS estimates (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    project_name TEXT,
                    location_zip TEXT,
                    status TEXT,
                    created_at TEXT,
                    reviewed_at TEXT,
                    reviewer_id TEXT,
                    raw_extraction TEXT,
                    approved_materials TEXT,
                    final_estimate TEXT,
                    file_path TEXT,
                    file_size INTEGER
                )
            """)

            c.execute("""
                INSERT INTO estimates
                (id, filename, project_name, location_zip, status, created_at, file_path, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                estimate_id,
                filename,
                project_name,
                location_zip,
                "uploaded",
                datetime.now().isoformat(),
                file_path,
                file_size
            ))

            conn.commit()
            logger.info(f"Created estimate record: {estimate_id}")

        finally:
            conn.close()

    def _save_extraction_results(
        self,
        estimate_id: str,
        materials: List[ExtractedMaterial],
        avg_confidence: float
    ):
        """Save extracted materials to database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            # Convert materials to JSON
            materials_json = json.dumps([
                {
                    "id": m.id,
                    "name": m.name,
                    "quantity": m.quantity,
                    "unit": m.unit,
                    "category": m.category,
                    "confidence": m.confidence,
                    "specifications": m.specifications or {},
                    "room_location": m.room_location
                }
                for m in materials
            ])

            c.execute("""
                UPDATE estimates
                SET status = ?, raw_extraction = ?
                WHERE id = ?
            """, (
                "pending_review",
                materials_json,
                estimate_id
            ))

            conn.commit()
            logger.info(f"Saved extraction results for {estimate_id} ({len(materials)} materials)")

        finally:
            conn.close()

    def get_upload_status(self, estimate_id: str) -> Dict[str, Any]:
        """Get status of an uploaded blueprint."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute("""
                SELECT id, filename, project_name, status, created_at, raw_extraction
                FROM estimates
                WHERE id = ?
            """, (estimate_id,))

            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Estimate not found")

            raw_extraction = json.loads(row[5]) if row[5] else []

            return {
                "estimate_id": row[0],
                "filename": row[1],
                "project_name": row[2],
                "status": row[3],
                "created_at": row[4],
                "materials_extracted": len(raw_extraction),
                "avg_confidence": (
                    sum(m.get("confidence", 0) for m in raw_extraction) / len(raw_extraction)
                    if raw_extraction else 0
                )
            }

        finally:
            conn.close()
