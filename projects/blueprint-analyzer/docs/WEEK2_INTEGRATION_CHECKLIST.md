# Week 2 Integration - Quick Reference Checklist

**Status:** 9/12 tasks complete (75%) | 3 tasks remaining  
**Timeline:** 2-3 hours to completion  
**Target:** Full E2E pipeline functional TODAY

---

## Tasks Summary

### ✅ COMPLETED (5/12)

- [x] Task #1: E2E Test Framework
  - Location: `tests/test_e2e_pipeline.py`
  - Deliverables: 7 tests, PipelineValidator, MockData
  - Status: Ready for integration testing

- [x] Task #2: API ↔ Preprocessing
  - Location: `hermes/blueprint_analysis/api/preprocessing_integration.py`
  - Deliverables: PreprocessingClient, FileUploadHandler, FastAPI routes
  - Status: Upload endpoint live

- [x] Task #3: Preprocessing ↔ Claude Vision
  - Location: `hermes/blueprint_analysis/claude_vision/integration.py`
  - Deliverables: ClaudeVisionIntegration, Tier 1 prompt, Response parser
  - Status: Material extraction ready

- [x] Task #4: Claude Vision ↔ Material Matching
  - Location: `hermes/blueprint_analysis/materials/cv_integration.py`
  - Deliverables: ClaudeVisionMaterialMatchingBridge, MaterialMatchingValidator, 9 tests
  - Status: Fuzzy matching + unit conversion working

- [x] Task #5: Material Matching ↔ Pricing
  - Location: `hermes/blueprint_analysis/pricing/mm_integration.py`
  - Deliverables: MaterialMatchingPricingBridge, PricingValidator, multi-source lookup
  - Status: Regional pricing + supplier tracking complete

---

## Tasks Queue (7 Remaining)

### Task #6: Labor Calculation Integration
**Blocked by:** Task #5 ✅  
**Est. time:** 1 hour  
**Template:** See INTEGRATION_TASK_TEMPLATES.md - Task #6 section

**Steps:**
1. Create `hermes/blueprint_analysis/labor/integration.py`
2. Implement `PricingLaborBridge`
3. Wire to labor service (already built, Agent 6)
4. Write 3 integration tests
5. Mark task complete

---

### Task #7: API Aggregation
**Blocked by:** Task #6  
**Est. time:** 1 hour  
**Template:** See INTEGRATION_TASK_TEMPLATES.md - Task #7 section

**Steps:**
1. Create `hermes/blueprint_analysis/api/routes_aggregation.py`
2. Implement `ResponseAggregator` class
3. Combine all outputs into BlueprintAnalysisResponse
4. Test aggregation logic
5. Mark task complete

**Critical functions:**
- `aggregate()` — Combines materials + pricing + labor
- `_calculate_confidence()` — Weighted average
- `_breakdown_by_category()` — Summary calculations

---

### Task #8: Frontend Integration
**Blocked by:** Task #7  
**Est. time:** 1 hour  
**Template:** See INTEGRATION_TASK_TEMPLATES.md - Task #8 section

**Steps:**
1. Create `hermes/blueprint_analysis/api/routes_frontend.py`
2. Implement `GET /estimates/{id}` endpoint
3. Transform response for React UI
4. Implement export endpoints (PDF, CSV, JSON)
5. Test with frontend mock
6. Mark task complete

**Key endpoints:**
- `GET /estimates/{id}` — Fetch estimate for display
- `POST /estimates/{id}/export` — Export in various formats

---

### Task #9: Pricing Trends Integration
**Blocked by:** Task #8  
**Est. time:** 30 minutes  
**Template:** See INTEGRATION_TASK_TEMPLATES.md - Task #9 section

**Steps:**
1. Create `hermes/blueprint_analysis/pricing_trends/estimate_integration.py`
2. Implement `PricingTrendsRecorder` class
3. Wire into estimate aggregation
4. Store daily price snapshots
5. Mark task complete

---

### Task #10: E2E Pipeline Testing
**Blocked by:** Task #9  
**Est. time:** 1 hour

**Steps:**
1. Update E2E test framework with real integrations
2. Run full pipeline tests: `pytest tests/test_e2e_pipeline.py -v`
3. Validate data flow through all 9 agents
4. Measure performance metrics
5. Document results
6. Mark task complete

**Expected results:**
- Kitchen remodel: <2 min total latency
- 85%+ confidence score
- All data contracts validated
- Zero regressions

---

### Task #11: Bug Fixes & Integration Issues
**Blocked by:** Task #10  
**Est. time:** 2-3 hours

**Steps:**
1. Document any failures from Task #10
2. Fix data format mismatches
3. Resolve timing issues
4. Improve error handling
5. Validate error messages
6. Re-run tests
7. Mark task complete

**Common issues to watch:**
- Data type mismatches between agents
- Missing optional fields
- Timing/latency issues
- Error handling edge cases

---

### Task #12: Beta Preparation
**Blocked by:** Task #11  
**Est. time:** 1 hour

**Steps:**
1. Deploy to staging (Docker)
2. Verify all endpoints accessible
3. Test with 3-5 real customer blueprints
4. Setup human reviewer dashboard
5. Prepare beta customer docs
6. Mark task complete

**Readiness checklist:**
- [ ] All endpoints functional
- [ ] Error handling working
- [ ] Performance acceptable (<2 min)
- [ ] Hybrid mode (AI + human review) active
- [ ] Documentation ready
- [ ] Team trained on reviewer dashboard

---

## Daily Execution Plan

### COMPLETED
- ✅ Task #4: Material Matching (1.5h)
- ✅ Task #5: Pricing (1.5h)

### Day 1 (Today)
- Task #6: Labor (1h)
- Task #7: API Aggregation (1h)
- **Subtotal: 2 hours**

### Day 2 (Tomorrow)
- Task #8: Frontend (1h)
- Task #9: Pricing Trends (0.5h)
- Task #10: E2E Tests (1h)
- **Subtotal: 2.5 hours**

### Day 3 (Next Day)
- Task #11: Bug Fixes (1-2h)
- Task #12: Beta Prep (1h)
- **Subtotal: 2-3 hours**

**Total: 6.5-7.5 hours remaining** → **Full system complete by end of Day 3**

---

## Success Criteria

✅ **All tasks complete when:**

1. **All 12 tasks marked completed**
2. **E2E pipeline passes all tests**
3. **Performance targets met** (<2 min per blueprint)
4. **Confidence scores calibrated** (85%+)
5. **Zero regressions** from previous work
6. **Error handling verified** (graceful degradation)
7. **Data contracts validated** (all schemas match)
8. **System ready for Week 3 beta**

---

## Reference Commands

```bash
# Run all integration tests
pytest tests/test_*_integration.py -v

# Run E2E pipeline tests
pytest tests/test_e2e_pipeline.py -v

# Run specific task tests
pytest tests/test_task_4_integration.py -v

# Check all tests pass
pytest tests/ -q

# Docker stack (when ready)
docker-compose up -d

# Verify endpoints
curl http://localhost:8000/api/v1/health
```

---

## Notes

- **Templates provided** in `INTEGRATION_TASK_TEMPLATES.md`
- **Each task follows same pattern** → reproducible, fast
- **Tests included** for each task
- **Error handling standardized** across all agents
- **Data contracts validated** at each step

**Ready to execute. 3 complete, 9 to go. 🚀**

