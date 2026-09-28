# LLM Backends for Training Data Generation

Choose which LLM to use for generating 2,000 training examples. Pipeline supports multiple backends:

## Quick Start (Recommended: DeepSeek - FREE)

```bash
# 1. Get free API key
curl -X POST https://platform.deepseek.com/api/v1/auth/register -d '{"username":"your-email"}'
# Copy the API key

# 2. Set environment variable
export DEEPSEEK_API_KEY="sk-..."

# 3. Update config (optional, DeepSeek is default)
# Edit config.yaml: llm.backend: "deepseek"

# 4. Run pipeline
bash qwen-finetuning/run_pipeline.sh
```

---

## Backend Comparison

| Backend | Cost | Quality | Speed | Setup |
|---------|------|---------|-------|-------|
| **DeepSeek** ⭐ | FREE | ⭐⭐⭐⭐⭐ | Fast | Easy |
| **Gemini** | $300 free | ⭐⭐⭐⭐ | Fast | Easy |
| **ChatGPT** | $0.002/1K | ⭐⭐⭐ | Fast | Easy |
| **Claude** | $0.003/1K | ⭐⭐⭐⭐⭐ | Slow | Easy |

---

## Detailed Setup Instructions

### 1. DeepSeek (Recommended - FREE)

**Why:** Best free option, excellent reasoning quality, no credit card needed

```bash
# Step 1: Get free API key
# Visit: https://platform.deepseek.com/
# Sign up → Create API key

# Step 2: Set environment variable
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxx"

# Step 3: Update config.yaml (if needed)
# llm:
#   backend: "deepseek"  # Already default

# Step 4: Run
ssh garage-core "cd qwen-finetuning && \
  export DEEPSEEK_API_KEY='sk-...' && \
  bash run_pipeline.sh"

# Cost: $0 (free tier available)
# For 2,000 examples: ~$2-5 if you exceed free tier
```

**Pros:**
- Free API with reasonable limits
- Excellent reasoning (better than GPT-3.5)
- No credit card required
- Fast generation

**Cons:**
- May have rate limits on free tier
- Slightly lower quality than Claude

---

### 2. Google Gemini (FREE - $300 credits)

**Why:** Free $300 credits, fast, no rate limits during credits

```bash
# Step 1: Get free API key
# Visit: https://aistudio.google.com/app/apikey
# Click "Create API key" → Copy

# Step 2: Set environment variable
export GEMINI_API_KEY="AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Step 3: Update config.yaml
# llm:
#   backend: "gemini"

# Step 4: Run
ssh garage-core "cd qwen-finetuning && \
  export GEMINI_API_KEY='AIzaSy...' && \
  bash run_pipeline.sh"

# Cost: FREE ($300 free credits)
# Estimated usage: ~$10-15 of credits
```

**Pros:**
- $300 free credits (plenty for this)
- Fast and reliable
- No rate limits during free tier

**Cons:**
- Credits expire (90 days)
- Slightly lower quality than Claude

---

### 3. OpenAI ChatGPT (Cheap - $0.002/1K tokens)

**Why:** Cheapest paid option, fast, good for cost-conscious

```bash
# Step 1: Get API key
# Visit: https://platform.openai.com/account/api-keys
# Click "Create new secret key" → Copy

# Step 2: Set environment variable
export OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxx"

# Step 3: Update config.yaml
# llm:
#   backend: "chatgpt"

# Step 4: Run
ssh garage-core "cd qwen-finetuning && \
  export OPENAI_API_KEY='sk-proj-...' && \
  bash run_pipeline.sh"

# Cost: ~$2-5 for 2,000 examples (gpt-3.5-turbo)
# Much cheaper than Claude ($6-10)
```

**Pros:**
- Very cheap
- Fast
- Reliable

**Cons:**
- Requires credit card
- Lower quality than Claude/DeepSeek

---

### 4. Claude (Best Quality - Paid)

**Why:** Highest quality responses, best reasoning

```bash
# Step 1: Get API key
# Visit: https://console.anthropic.com/account/keys
# Click "Create Key" → Copy

# Step 2: Set environment variable
export CLAUDE_API_KEY="sk-ant-xxxxxxxxxxxxxxxxxxxxx"

# Step 3: Update config.yaml
# llm:
#   backend: "claude"

# Step 4: Run
ssh garage-core "cd qwen-finetuning && \
  export CLAUDE_API_KEY='sk-ant-...' && \
  bash run_pipeline.sh"

# Cost: ~$6-10 for 2,000 examples (claude-opus-5)
```

**Pros:**
- Highest quality training data
- Best reasoning
- Most reliable

**Cons:**
- Most expensive (~$10)
- Slowest generation

---

## Cost Summary (For 2,000 Examples)

| Backend | Total Cost | Per 1000 |
|---------|-----------|---------|
| DeepSeek | $0-5 | $0-2.50 |
| Gemini | $0 (free credits) | $0 |
| ChatGPT | $2-5 | $1-2.50 |
| Claude | $6-10 | $3-5 |

---

## How to Change Backend Mid-Pipeline

If you start generating data and want to switch:

```bash
# 1. Edit config.yaml
llm:
  backend: "gemini"  # Change to desired backend

# 2. Set new API key
export GEMINI_API_KEY="AIzaSy..."

# 3. Resume from where you left off
# The script will continue generating examples
python 1_generate_data.py
```

---

## Troubleshooting

### "API key not set" error
```bash
# Make sure environment variable is exported
export DEEPSEEK_API_KEY="sk-..."
echo $DEEPSEEK_API_KEY  # Should print your key
```

### Rate limit hit
```bash
# Try different backend or wait for limits to reset
# DeepSeek: ~60 requests/minute on free tier
# Gemini: Unlimited with free credits
# ChatGPT: Unlimited with paid account
```

### Quality too low
```bash
# Use higher quality backend
# Ranking: Claude > DeepSeek > Gemini > ChatGPT
# Or increase max_tokens in config.yaml
max_tokens: 2500  # Was 2000
```

### Pipeline slow
```bash
# Use faster backend
# Ranking speed: Gemini > ChatGPT > DeepSeek > Claude
# Or reduce num_epochs in config.yaml
num_epochs: 1  # Was 3 (test only)
```

---

## Recommendation Matrix

**Budget: $0** → Use DeepSeek (free, high quality)
**Budget: $5** → Use Gemini free credits or ChatGPT
**Budget: $10+** → Use Claude (best quality)
**Speed critical** → Use Gemini or ChatGPT
**Quality critical** → Use Claude or DeepSeek

---

## After Training: Which LLM to Use for Evaluation?

Step 4 (evaluate.py) uses Claude to score the fine-tuned model. You can change this too:

```yaml
# In config.yaml - evaluation can use different backend than generation
evaluation:
  backend: "claude"  # Higher quality for scoring
```

Recommendation: Use Claude for evaluation (step 4) only, DeepSeek for generation (step 1).
This balances cost and quality.

---

**Questions?** Check the logs in `qwen-finetuning/logs/` for detailed API responses.
