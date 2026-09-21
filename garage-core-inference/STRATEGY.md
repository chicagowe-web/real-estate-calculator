# GPU-Optimized Inference Strategy

Use garage-core's GPU to run all agent inference locally, minimizing API token usage.

## Architecture

```
Agents (Hermes, AgentUptoDate, ResearchAgent, MonitoringAgent)
    ↓
Inference Router (routes to garage-core)
    ↓
garage-core GPU via Ollama
    ├─ gemma4:e4b      (fast, general inference)
    ├─ gemma4:26b      (complex reasoning)
    └─ garage-ai-v12   (automotive diagnostics)
    
Result: Heavy lifting done locally, API calls only for:
  - WebSearch (external, unavoidable)
  - WebFetch (external, unavoidable)
  - Final synthesis where needed
```

## Agent Optimizations

### 1. Hermes (Task Orchestration)
**Current:** Uses Ollama on garage-core ✅
**Already optimized** — all inference local

### 2. AgentUptoDate (System Updates)
**Current:** No LLM inference yet
**Optimize:**
- Use local LLM to: analyze update risks, generate remediation commands
- Instead of: "ask Claude to analyze this update"
- Do: `ollama generate "what are risks of updating Python 3.11→3.12?"`

**Code:**
```python
# Instead of external API:
response = await ollama_client.generate(
    model="gemma4:e4b",
    prompt=f"Analyze security update: {update_description}",
    stream=False
)
```

### 3. ResearchAgent (Multi-source Research)
**Current:** Uses WebSearch/WebFetch (unavoidable), but synthesizes with... nothing
**Optimize:**
- Use local LLM to: summarize search results, extract key points, generate report
- Instead of: sending raw results to Claude
- Do: `ollama generate "summarize these research findings..."`

**Code:**
```python
# Gather web results (WebSearch/WebFetch)
findings = await web_search.search("topic")

# Synthesize locally instead of external API
summary = await ollama_client.generate(
    model="gemma4:26b",
    prompt=f"""Synthesize these research findings:
    {findings}
    
    Generate: overview, best practices, pitfalls, pro tips"""
)
```

### 4. MonitoringAgent (Infrastructure Monitoring)
**Current:** Generates basic alerts
**Optimize:**
- Use local LLM to: write alert descriptions, suggest Hermes actions, explain anomalies
- Instead of: hardcoded strings
- Do: `ollama generate "explain this GPU anomaly..."`

**Code:**
```python
# Instead of hardcoded alert descriptions:
description = f"{metric} at {value}% (threshold: {threshold}%)"

# Do: generate intelligent explanation
explanation = await ollama_client.generate(
    model="gemma4:e4b",
    prompt=f"""Alert: {metric} anomaly
    Device: {device}
    Current: {current_value}%
    Expected: {expected_value}%
    
    Provide: brief explanation, severity assessment, suggested fix via Hermes"""
)
```

## Token Savings

### Before (Using Claude API)
```
ResearchAgent research call:
  - WebSearch (external, ~5 calls)
  - WebFetch (external, ~3 calls)
  - Claude synthesis: ~2000 tokens

MonitoringAgent anomaly:
  - Claude explanation: ~500 tokens per alert × 10 alerts = 5000 tokens/day

AgentUptoDate update analysis:
  - Claude risk assessment: ~1000 tokens × 5 updates = 5000 tokens/week

Total: ~15,000 tokens/day = ~450,000 tokens/month
```

### After (Using garage-core GPU)
```
ResearchAgent research call:
  - WebSearch (external, ~5 calls)
  - WebFetch (external, ~3 calls)
  - Ollama synthesis: 0 tokens (local GPU)

MonitoringAgent anomaly:
  - Ollama explanation: 0 tokens (local GPU)

AgentUptoDate update analysis:
  - Ollama risk assessment: 0 tokens (local GPU)

Total: ~0 tokens/day = ~0 tokens/month
API Usage: ~10% (WebSearch only, unavoidable)
```

## Implementation

### 1. Create Inference Client

```python
# garage_core_inference.py
class GarageCoreInference:
    def __init__(self, ollama_url="http://192.168.0.129:11434"):
        self.ollama_url = ollama_url
        self.models = {
            "fast": "gemma4:e4b",
            "reasoning": "gemma4:26b",
            "automotive": "garage-ai-v12:latest"
        }
    
    async def generate(self, prompt, model_type="fast"):
        """Call Ollama on garage-core"""
        model = self.models[model_type]
        response = await self.ollama_client.generate(
            model=model,
            prompt=prompt,
            stream=False
        )
        return response
    
    async def summarize_findings(self, findings):
        """Synthesize research findings"""
        prompt = f"""Summarize these research findings into a report:
        
{findings}

Generate: overview (2-3 sentences), best practices (5), pitfalls (3), pro tips (3)"""
        return await self.generate(prompt, model_type="reasoning")
    
    async def explain_anomaly(self, device, metric, values):
        """Explain an anomaly"""
        prompt = f"""Explain this infrastructure anomaly:
        
Device: {device}
Metric: {metric}
Pattern: {values}

Provide: brief explanation, likely cause, suggested fix"""
        return await self.generate(prompt, model_type="fast")
    
    async def assess_update_risk(self, update_description):
        """Assess update risks"""
        prompt = f"""Assess the risk of this system update:
        
{update_description}

Provide: risk level (low/medium/high), potential issues, rollback plan"""
        return await self.generate(prompt, model_type="fast")
```

### 2. Integrate with Agents

**ResearchAgent:**
```python
# In report_builder.py
async def generate_overview(self, topic, resources):
    """Use Ollama instead of Claude API"""
    findings = format_findings(resources)
    
    inference = GarageCoreInference()
    overview = await inference.summarize_findings(findings)
    
    return overview  # No API call!
```

**MonitoringAgent:**
```python
# In alert_system.py
async def create_anomaly_alert(self, device, metric, values):
    """Use Ollama for explanation"""
    inference = GarageCoreInference()
    explanation = await inference.explain_anomaly(device, metric, values)
    
    alert.description = explanation  # Generated locally!
    return alert
```

**AgentUptoDate:**
```python
# In update_analyzer.py
async def analyze_update(self, update):
    """Use Ollama for risk assessment"""
    inference = GarageCoreInference()
    risk = await inference.assess_update_risk(update.description)
    
    return risk  # No API call!
```

### 3. When to Use Local vs API

| Task | Use | Reason |
|------|-----|--------|
| Summarize findings | Local (Ollama) | No external knowledge needed |
| Explain metrics | Local (Ollama) | Statistical explanation |
| Generate commands | Local (Ollama) | Pattern matching |
| Complex reasoning | Local (gemma4:26b) | Advanced thinking |
| **Web search** | **API (WebSearch)** | **Needs current data** |
| **Web fetch** | **API (WebFetch)** | **Needs live content** |
| Final report synthesis | Local (Ollama) | Known information only |

## Garage-core Resource Usage

**Current:** ~60% GPU utilization (Garage-AI v14 training)
**Available:** ~40% for agent inference

```
GPU Memory Breakdown:
  Garage-AI v14:    30GB (training)
  Available:        16GB
  
  Needed for:
  - gemma4:e4b:     ~4GB
  - gemma4:26b:     ~17GB (don't load simultaneously)
  - Reserve:        ~4GB
  
  Strategy: Load gemma4:e4b always, swap in gemma4:26b when needed
```

## Performance Impact

**Latency:**
- Local inference: 200-500ms (very fast)
- API call: 1-2s (network + queue)
- Network overhead: 50ms

**Inference speeds:**
- gemma4:e4b: ~50 tokens/sec (fast)
- gemma4:26b: ~20 tokens/sec (slower but better)

**Typical workload:**
- ResearchAgent summary: 500 tokens @ 50 tokens/sec = 10 seconds
- MonitoringAgent explanation: 100 tokens @ 50 tokens/sec = 2 seconds
- AgentUptoDate analysis: 300 tokens @ 50 tokens/sec = 6 seconds

## Configuration

```yaml
# ~/.agents/inference.yaml
garage_core:
  host: 192.168.0.129
  port: 11434
  
models:
  default: gemma4:e4b         # Fast, general
  reasoning: gemma4:26b       # Slower, smarter
  automotive: garage-ai-v12   # Specialized
  
inference:
  timeout_seconds: 30
  max_tokens: 1000
  temperature: 0.7
  
routing:
  research_synthesis: reasoning      # Use gemma4:26b
  monitor_alerts: default             # Use gemma4:e4b
  update_analysis: default            # Use gemma4:e4b
  automotive_diagnostic: automotive   # Use Garage-AI
```

## Fallback Strategy

If garage-core GPU is unavailable:
1. Try fallback to local CPU (slow but works)
2. Queue the inference for later
3. Use pre-generated templates (no inference)
4. Fall back to Claude API (token cost)

```python
async def generate_with_fallback(self, prompt, priority="normal"):
    try:
        # Try garage-core GPU first
        return await self.ollama_client.generate(prompt)
    except Exception as e:
        if priority == "high":
            # Fall back to Claude API for critical alerts
            return await claude_client.generate(prompt)
        else:
            # Use template for non-critical
            return self.template_response(prompt)
```

## Monitoring Inference Load

Track GPU inference usage:

```
MonitoringAgent watches:
  - GPU VRAM usage
  - Inference queue depth
  - Average response time
  - Tokens/sec throughput
  
Alert if:
  - GPU VRAM > 90%
  - Inference queue > 10 items
  - Response time > 5 seconds
  - Training interrupted by inference load
```

## Summary

**Before:** 450K tokens/month via API
**After:** ~0 tokens/month (except unavoidable WebSearch)

**How:** Route all synthesis, analysis, and explanation tasks to garage-core's local GPU via Ollama.

**Cost:** ~40% of garage-core's existing GPU capacity
**Benefit:** 99% reduction in API token usage

---

**Status:** Ready to implement. Requires:
1. Create `GarageCoreInference` client
2. Update each agent to use local inference
3. Add fallback handling
4. Monitor GPU usage
