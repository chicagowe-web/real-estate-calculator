#!/usr/bin/env python3
"""
Quick start: Launch dashboard with demo data.

Run this to:
1. Create demo estimate in database
2. Start backend server
3. Open dashboard in browser
"""

import sqlite3
import json
import subprocess
import time
import sys
import os
import webbrowser
from datetime import datetime
from pathlib import Path


def create_demo_estimate():
    """Create sample estimate in database."""
    db_path = "/tmp/blueprint_reviews.db"

    # Create database if not exists
    db = sqlite3.connect(db_path)
    c = db.cursor()

    # Create tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS estimates (
            id TEXT PRIMARY KEY,
            filename TEXT,
            project_name TEXT,
            location_zip TEXT,
            status TEXT,
            created_at TEXT,
            reviewed_at TEXT,
            reviewer_id TEXT DEFAULT 'reviewer_1',
            raw_extraction JSON,
            approved_materials JSON,
            final_estimate JSON
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS review_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id TEXT,
            action_type TEXT,
            material_id TEXT,
            old_value TEXT,
            new_value TEXT,
            timestamp TEXT,
            reviewer_id TEXT DEFAULT 'reviewer_1'
        )
    """)

    # Clear existing demo data
    c.execute("DELETE FROM estimates WHERE id LIKE 'est_demo_%'")

    # Insert demo estimate
    demo_materials = [
        {
            "id": "mat_001",
            "name": "Drywall Sheet - 5/8\"",
            "quantity": 125,
            "unit": "sheets",
            "category": "drywall",
            "confidence": 0.92,
            "trades": ["drywall"]
        },
        {
            "id": "mat_002",
            "name": "2x4 Stud - SPF",
            "quantity": 250,
            "unit": "pieces",
            "category": "framing",
            "confidence": 0.88,
            "trades": ["framing"]
        },
        {
            "id": "mat_003",
            "name": "Electrical Cable - 12/2 Romex",
            "quantity": 500,
            "unit": "linear_feet",
            "category": "electrical",
            "confidence": 0.62,  # Low - needs review
            "trades": ["electrical"]
        },
        {
            "id": "mat_004",
            "name": "Interior Paint - Eggshell",
            "quantity": 30,
            "unit": "gallons",
            "category": "paint",
            "confidence": 0.95,
            "trades": ["painting"]
        },
        {
            "id": "mat_005",
            "name": "HVAC Ductwork - 6\" Diameter",
            "quantity": 200,
            "unit": "linear_feet",
            "category": "hvac",
            "confidence": 0.58,  # Low - needs review
            "trades": ["hvac"]
        }
    ]

    c.execute("""
        INSERT INTO estimates
        (id, filename, project_name, location_zip, status, created_at, raw_extraction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "est_demo_001",
        "office_building.pdf",
        "Downtown Office Renovation - 2nd Floor",
        "60601",
        "pending",
        datetime.now().isoformat(),
        json.dumps(demo_materials)
    ))

    # Add a second demo estimate
    demo_materials_2 = [
        {
            "id": "mat_101",
            "name": "Granite Countertop",
            "quantity": 25,
            "unit": "linear_feet",
            "category": "countertops",
            "confidence": 0.91,
            "trades": ["countertops"]
        },
        {
            "id": "mat_102",
            "name": "Cabinet Hardware - Stainless Steel",
            "quantity": 45,
            "unit": "pieces",
            "category": "hardware",
            "confidence": 0.85,
            "trades": ["carpentry"]
        },
        {
            "id": "mat_103",
            "name": "Faucet - Single Handle",
            "quantity": 3,
            "unit": "pieces",
            "category": "plumbing",
            "confidence": 0.88,
            "trades": ["plumbing"]
        }
    ]

    c.execute("""
        INSERT INTO estimates
        (id, filename, project_name, location_zip, status, created_at, raw_extraction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "est_demo_002",
        "kitchen_remodel.pdf",
        "Kitchen Remodel - High-End Finishes",
        "60610",
        "pending",
        datetime.now().isoformat(),
        json.dumps(demo_materials_2)
    ))

    db.commit()
    db.close()

    print("✅ Demo estimates created")
    print(f"   Database: {db_path}")
    print(f"   Estimate 1: est_demo_001 (Office Renovation - 5 materials)")
    print(f"   Estimate 2: est_demo_002 (Kitchen Remodel - 3 materials)")


def start_server():
    """Start FastAPI backend server."""
    print("\n🚀 Starting dashboard backend server...")
    print("   Port: 8001")
    print("   Press Ctrl+C to stop\n")

    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "hermes.blueprint_analysis.reviewer.backend:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        "--reload"
    ]

    subprocess.run(cmd, cwd="/home/tp/.claude/worktrees/dashboard-launch")


def main():
    """Main flow."""
    print("=" * 60)
    print("BLUEPRINT ANALYZER - Dashboard Demo Launcher")
    print("=" * 60)

    # Step 1: Create demo data
    print("\n[1/3] Creating demo estimates...")
    create_demo_estimate()

    # Step 2: Open browser
    print("\n[2/3] Opening dashboard in browser...")
    time.sleep(1)

    try:
        webbrowser.open("http://localhost:8001")
        print("✅ Dashboard URL: http://localhost:8001")
    except Exception as e:
        print(f"⚠️  Could not auto-open browser: {e}")
        print("   Manually open: http://localhost:8001")

    # Step 3: Start server
    print("\n[3/3] Starting FastAPI server...")
    time.sleep(1)

    print("\n" + "=" * 60)
    print("DEMO READY!")
    print("=" * 60)
    print("""
You should now see:
  - Two pending estimates in the sidebar
  - Click an estimate to view materials
  - High confidence items: green badges
  - Low confidence items: red badges (need review)

Try this:
  1. Click "Downtown Office Renovation"
  2. See 5 materials with confidence scores
  3. Change "Electrical Cable" quantity to 600 feet
  4. Click "Approve & Generate Estimate"

The system will:
  - Save your changes
  - Calculate material + labor costs
  - Generate final estimate JSON

Watch the terminal for API logs.
    """)
    print("=" * 60 + "\n")

    # Start server (blocking call)
    start_server()


if __name__ == "__main__":
    main()
