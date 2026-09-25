# Real Blueprint Testing Guide

**Status:** ✅ Test blueprints downloaded and ready  
**Date:** 2026-09-23  
**System:** Blueprint Analyzer v1.0 (Week 2 Integration Complete)

---

## Downloaded Blueprints

### 1. EdrawMax Bathroom Floor Plans
- **File:** `edraw_bathroom_plans.pdf` (1.9 MB, 27 pages)
- **Type:** Residential bathroom remodel layouts
- **Contents:** Multiple bathroom configurations with fixtures, dimensions, plumbing
- **Best For:** Testing bathroom renovation scenarios, fixture extraction, plumbing material identification

### 2. EdrawMax Blueprint Guide  
- **File:** `edraw_blueprint_guide.pdf` (2.0 MB, 23 pages)
- **Type:** Construction drawing standards + example plans
- **Contents:** Blueprint drafting standards, floor plans, kitchen & bathroom examples
- **Best For:** Testing material extraction on professional-grade documentation

### 3. Kirkland WA Sample Construction Set
- **File:** `kirkland_wa_sample_construction.pdf` (1.5 MB, 7 pages)
- **Type:** Official municipal construction document
- **Contents:** Complete residential construction details (structural, mechanical, electrical, plumbing)
- **Best For:** Testing full building system extraction, labor estimation across multiple trades

---

## Testing Instructions

### Step 1: Start API Server
```bash
cd /home/tp/projects/blueprint-analyzer
python -m uvicorn hermes.api.server:app --host 0.0.0.0 --port 8000 &
```

### Step 2: Upload Blueprint
```bash
# Test with bathroom remodel
curl -X POST \
  -F 'file=@/tmp/blueprint_test_images/edraw_bathroom_plans.pdf' \
  -F 'project_name=Bathroom Remodel' \
  -F 'location_zip=60601' \
  http://localhost:8000/api/v1/blueprints/upload

# Response: 202 Accepted
# {
#   "estimate_id": "est_xxxxxxxxxxxx",
#   "status": "processing",
#   "preprocessing_status": "queued",
#   "preprocessed_image_path": null,
#   "image_quality_score": 0.0,
#   "features": {}
# }
```

### Step 3: Check Processing Status
```bash
# Poll status endpoint every 5 seconds
curl http://localhost:8000/api/v1/blueprints/est_xxxxxxxxxxxx/status
```

### Step 4: Retrieve Final Estimate
```bash
# Once complete, get aggregated results
curl http://localhost:8000/api/v1/estimates/est_xxxxxxxxxxxx

# Response: BlueprintAnalysisResponse
# {
#   "estimate_id": "est_xxxxxxxxxxxx",
#   "status": "completed",
#   "materials": [...],
#   "pricing": [...],
#   "labor": [...],
#   "summary": {
#     "total_material_cost": 3450.00,
#     "total_labor_cost": 1200.00,
#     "total_estimated_cost": 4650.00,
#     "confidence_score": 0.87,
#     ...
#   }
# }
```

### Step 5: Validate Results
Compare extracted materials and costs against actual blueprint:

**Validation Checklist:**
- [ ] All visible materials identified (≥85%)
- [ ] Material quantities within ±10%
- [ ] Labor trades correctly classified
- [ ] Regional pricing applied
- [ ] Confidence scores in 0.70-1.0 range
- [ ] No critical errors
- [ ] Processing time <2 minutes

---

## Expected Accuracy Metrics

| Metric | Target | Method |
|--------|--------|--------|
| **Material Extraction** | 85%+ | Compare extracted to labeled items on blueprint |
| **Pricing Accuracy** | ±10% | Check against current Home Depot prices |
| **Labor Estimation** | ±15% | Compare to professional estimate for same scope |
| **Processing Time** | <2 min | Measure upload → final response |
| **Confidence Score** | 85%+ | System-calculated metric |

---

## Test Scenarios

### Scenario 1: Bathroom Remodel (EdrawMax Bathrooms PDF)
- **Estimated Materials:** 15-20 items (fixtures, tile, paint, etc.)
- **Estimated Labor:** 20-30 hours (plumbing, tile, painting)
- **Expected Cost:** $3,000-5,000
- **Primary Trades:** Plumbing, tiling, painting
- **Notes:** Good test for fixture extraction + specialty materials

### Scenario 2: Construction Standards (EdrawMax Guide PDF)
- **Estimated Materials:** 30-50 items (structural, mechanical, etc.)
- **Estimated Labor:** 40-60 hours
- **Expected Cost:** $6,000-10,000
- **Primary Trades:** Framing, electrical, plumbing, HVAC
- **Notes:** Complex document with multiple systems

### Scenario 3: Complete Construction (Kirkland WA PDF)
- **Estimated Materials:** 50+ items (complete residential)
- **Estimated Labor:** 100-200 hours
- **Expected Cost:** $15,000-30,000
- **Primary Trades:** All major trades
- **Notes:** Official municipal document - highest accuracy expected

---

## Known Limitations (Phase 1)

1. **Image quality affects extraction:** PDFs with diagrams work better than text-heavy documents
2. **Symbol recognition:** Electrical/plumbing symbols identified if visible
3. **Material specifications:** Extracted from labels/callouts, not inferred from context
4. **Hybrid review:** System ready for human review, dashboard integration pending
5. **PDF extraction:** Currently uses standard PDF text layer, no OCR for scanned images

---

## Success Criteria

✅ System ready when:
- [ ] All 3 blueprints upload without error
- [ ] Processing completes in <2 minutes each
- [ ] Material extraction ≥80% (80% of visible items identified)
- [ ] No critical errors in pricing or labor calculations
- [ ] Confidence scores 0.70+ for most materials
- [ ] Results appear reasonable vs. blueprint content

---

## Next Steps (Week 3)

1. **Manual Testing:** Upload blueprints and validate accuracy
2. **Accuracy Measurement:** Track extraction performance across 3 documents
3. **Human Review Dashboard:** Integrate reviewer feedback
4. **Production Deployment:** Deploy to staging after validation

---

## Contact & Support

For questions about test data:
- See `docs/INTEGRATION_TASK_TEMPLATES.md` for architecture
- See `docs/BETA_READINESS.md` for system status
- Check `docs/WEEK2_INTEGRATION_CHECKLIST.md` for task completion

**System Status:** ✅ Ready for real-world testing

