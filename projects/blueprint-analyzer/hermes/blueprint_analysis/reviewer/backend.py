"""
Hybrid Mode Review Dashboard Backend
Manages material extraction review workflow with Claude Vision integration
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import upload routes
from ..api.routes_upload import router as upload_router

app = FastAPI(
    title="Blueprint Review Dashboard",
    description="Material extraction and cost estimation for construction blueprints"
)

# Include upload routes
app.include_router(upload_router)

# Database setup
DB_PATH = Path("/tmp/blueprint_reviews.db")

def init_db():
    """Initialize review database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Estimates table
    c.execute('''
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
            final_estimate TEXT
        )
    ''')
    
    # Review actions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS review_actions (
            id TEXT PRIMARY KEY,
            estimate_id TEXT,
            action_type TEXT,
            material_id TEXT,
            old_value TEXT,
            new_value TEXT,
            timestamp TEXT,
            reviewer_id TEXT,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Models
class ExtractedMaterial(BaseModel):
    id: str
    name: str
    quantity: float
    unit: str
    category: str
    confidence: float
    trades: List[str] = []

class ReviewAction(BaseModel):
    estimate_id: str
    action_type: str  # "edit", "approve", "reject", "add", "remove"
    material_id: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class ReviewSummary(BaseModel):
    estimate_id: str
    total_materials: int
    approved: int
    needs_review: int
    rejected: int
    accuracy_score: float

# Routes
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "blueprint-review-dashboard"}

@app.get("/api/v1/review/pending")
async def get_pending_estimates():
    """Get list of pending review estimates"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT id, filename, project_name, location_zip, status, created_at
        FROM estimates
        WHERE status IN ('pending', 'in_review')
        ORDER BY created_at DESC
    """)
    
    estimates = []
    for row in c.fetchall():
        estimates.append({
            "id": row[0],
            "filename": row[1],
            "project_name": row[2],
            "location_zip": row[3],
            "status": row[4],
            "created_at": row[5]
        })
    
    conn.close()
    return {"estimates": estimates}

@app.get("/api/v1/review/{estimate_id}")
async def get_estimate_for_review(estimate_id: str):
    """Get estimate details for review"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT id, filename, project_name, status, raw_extraction, approved_materials
        FROM estimates
        WHERE id = ?
    """, (estimate_id,))
    
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    raw_extraction = json.loads(row[4]) if row[4] else []
    approved_materials = json.loads(row[5]) if row[5] else []
    
    return {
        "id": row[0],
        "filename": row[1],
        "project_name": row[2],
        "status": row[3],
        "raw_extraction": raw_extraction,
        "approved_materials": approved_materials,
        "extraction_accuracy": sum(m.get("confidence", 0) for m in raw_extraction) / len(raw_extraction) if raw_extraction else 0
    }

@app.post("/api/v1/review/{estimate_id}/action")
async def record_review_action(estimate_id: str, action: ReviewAction):
    """Record a reviewer action (approve, edit, reject)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Record action
    action_id = str(uuid.uuid4())
    c.execute("""
        INSERT INTO review_actions 
        (id, estimate_id, action_type, material_id, old_value, new_value, timestamp, reviewer_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        action_id,
        estimate_id,
        action.action_type,
        action.material_id,
        action.old_value,
        action.new_value,
        datetime.now().isoformat(),
        "reviewer_1"  # TODO: get from auth
    ))
    
    # Update estimate status
    c.execute("""
        UPDATE estimates
        SET status = 'in_review'
        WHERE id = ?
    """, (estimate_id,))
    
    conn.commit()
    conn.close()
    
    return {"action_id": action_id, "status": "recorded"}

@app.post("/api/v1/review/{estimate_id}/approve")
async def approve_estimate(estimate_id: str, approved_materials: List[Dict]):
    """Approve estimate after review"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Save approved materials
    c.execute("""
        UPDATE estimates
        SET status = 'approved',
            approved_materials = ?,
            reviewed_at = ?
        WHERE id = ?
    """, (
        json.dumps(approved_materials),
        datetime.now().isoformat(),
        estimate_id
    ))
    
    conn.commit()
    
    # Generate final estimate
    final_estimate = generate_final_estimate(approved_materials, estimate_id)
    
    c.execute("""
        UPDATE estimates
        SET final_estimate = ?
        WHERE id = ?
    """, (json.dumps(final_estimate), estimate_id))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "approved",
        "estimate_id": estimate_id,
        "final_estimate": final_estimate
    }

@app.get("/api/v1/review/{estimate_id}/export")
async def export_estimate(estimate_id: str, format: str = "json"):
    """Export final estimate"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT final_estimate, filename
        FROM estimates
        WHERE id = ?
    """, (estimate_id,))
    
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    estimate = json.loads(row[0]) if row[0] else {}
    filename = row[1]
    
    if format == "json":
        return JSONResponse(content=estimate)
    elif format == "pdf":
        # TODO: Generate PDF
        return {"error": "PDF export not yet implemented"}
    else:
        return {"error": f"Unknown format: {format}"}

def generate_final_estimate(materials: List[Dict], estimate_id: str) -> Dict:
    """Generate final estimate from approved materials"""
    
    # Calculate totals
    total_material = sum(m.get("total_price", 0) for m in materials)
    total_labor = sum(m.get("estimated_labor_cost", 0) for m in materials)
    
    return {
        "estimate_id": estimate_id,
        "timestamp": datetime.now().isoformat(),
        "materials": materials,
        "summary": {
            "total_material_cost": total_material,
            "total_labor_cost": total_labor,
            "total_estimated_cost": total_material + total_labor,
            "contingency": (total_material + total_labor) * 0.15,
            "final_with_contingency": (total_material + total_labor) * 1.15
        }
    }

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

