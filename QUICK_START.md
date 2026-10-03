# 🚀 Quick Start: Local LLM Agents for garage_core

## What You Have

✅ **Ollama running on garage_core** (192.168.1.200:11434)  
✅ **Excellent models ready to use:**
- `qwen2.5-coder:7b` — Fast coding LLM
- `qwen2.5-coder:14b` — Better quality
- `deepseek-coder:latest` — Ultra-compact
- `garage-ai-v14:latest` — Your custom automotive model

✅ **Network connectivity** between your laptop and garage_core  
✅ **RTX 3080** for fast inference

## 5-Minute Setup

### Step 1: Copy the MCP Server (1 min)

```bash
mkdir -p ~/.claude/mcp
cp agents/ollama-mcp-server.py ~/.claude/mcp/
chmod +x ~/.claude/mcp/ollama-mcp-server.py
```

### Step 2: Update Claude Code Settings (2 min)

Edit `~/.claude/settings.json`:

```json
{
  "mcp": {
    "ollama-local": {
      "command": "python3",
      "args": ["/Users/YOUR_USERNAME/.claude/mcp/ollama-mcp-server.py"]
    }
  }
}
```

Replace `YOUR_USERNAME` with your actual username.

### Step 3: Test It Works (2 min)

In your terminal:

```bash
# Test Ollama is running
curl -s http://192.168.1.200:11434/api/tags | jq '.models[0].name'

# Test MCP server
echo '{"method":"list_tools","params":{}}' | python3 ~/.claude/mcp/ollama-mcp-server.py
```

You should see model names and JSON with tool definitions.

## Your First Agent: Code Review

### Quick Test

Open Claude Code and create a simple test:

```bash
cat > /tmp/test.py << 'EOF'
# Test code for review
def add(a,b):
    return a+b
x = add(1, 2)
print(x)
EOF

# Review it with local LLM
echo '{"method":"call_tool","params":{"name":"code_review","input":{"code":"def add(a,b):\n    return a+b\nx=add(1,2)","language":"python"}}}' | python3 ~/.claude/mcp/ollama-mcp-server.py
```

You'll get feedback from qwen2.5-coder without any API calls!

## Three Types of Agents You Can Create

### 1️⃣ Interactive Agents (Slash Commands)

Type in Claude Code terminal:

```bash
/code-review-local src/my_file.py
```

This reviews code with local LLM instantly.

### 2️⃣ Scheduled Agents

Run on a timer:

```bash
/loop 5m

Check vehicle diagnostics from /data/diagnostics/latest.json
Analyze with garage-ai-v14 model
Alert if any error codes found
```

### 3️⃣ Event-Triggered Agents

Run on git hooks:

```json
{
  "hooks": {
    "post-commit": "python3 agents/code-review-local.py HEAD~1..HEAD"
  }
}
```

## Example Agent: Hermes OS Research

Run the research agent:

```bash
python3 agents/example-hermes-research-agent.py
```

This will:
- Analyze YouTube videos on Hermes OS
- Check forums and discussions
- Review documentation
- Find integration opportunities
- Generate recommendations

Output: `/data/research/hermes-analysis.json`

## Key Models to Use

| Task | Model | Why |
|------|-------|-----|
| Quick code reviews | qwen2.5-coder:7b | Fast, good enough |
| Better reviews | qwen2.5-coder:14b | More accurate |
| Vehicle diagnostics | garage-ai-v14 | Your fine-tuned model |
| General reasoning | hermes3 | Fast thinking |
| Ultra-fast | deepseek-coder | Compact, 1B params |

## Why Local LLM?

✅ **No API costs** — Free after download  
✅ **No API latency** — Results in seconds  
✅ **Privacy** — Code stays on your network  
✅ **Offline** — Works without internet  
✅ **Specialized** — Use garage-ai-v14 for automotive  
✅ **Always available** — No rate limits  

## Next: Build Your Agent Fleet

### Agent 1: Vehicle Diagnostics (5 min)

```bash
cat > ~/.claude/agents/diagnostic-agent.sh << 'EOF'
#!/bin/bash
# Monitor vehicle health every 5 minutes

DATA=$(cat /data/diagnostics/latest.json)
ANALYSIS=$(curl -s http://192.168.1.200:11434/api/generate \
  -d "{\"model\": \"garage-ai-v14:latest\", \"prompt\": \"Analyze this diagnostic data: $DATA\", \"stream\": false}" \
  | jq -r '.response')

echo "$ANALYSIS" | tee -a /var/log/diagnostics.log

if echo "$ANALYSIS" | grep -qi "error\|critical"; then
  echo "🚨 ALERT: Vehicle issue detected!"
fi
EOF
chmod +x ~/.claude/agents/diagnostic-agent.sh
```

### Agent 2: Code Quality (1 min)

Use the MCP server you just created:

```bash
# In Claude Code, type:
/code-review-local HEAD~1..HEAD
```

This reviews your latest commit with local LLM.

### Agent 3: Research (already done!)

```bash
python3 agents/example-hermes-research-agent.py
```

This analyzes Hermes OS for you.

## Common Operations

### List available models

```bash
ssh garage-core "ollama list"
```

### Pull a new model

```bash
ssh garage-core "ollama pull mistral"
```

### Check Ollama status

```bash
ssh garage-core "systemctl status ollama"
```

### See MCP tools available

```bash
echo '{"method":"list_tools","params":{}}' | python3 ~/.claude/mcp/ollama-mcp-server.py | jq '.tools[].name'
```

## Troubleshooting

**"Connection refused"**
```bash
ssh garage-core "systemctl restart ollama"
```

**"Model not found"**
```bash
ssh garage-core "ollama pull qwen2.5-coder:7b"
```

**MCP server not responding**
```bash
python3 --version  # Should be 3.8+
which python3      # Should be /usr/bin/python3 or similar
```

## What You Can Do Now

- ✅ Review code with local LLM (no API calls)
- ✅ Run diagnostic analysis on vehicle data
- ✅ Research Hermes OS automatically
- ✅ Build custom agents that use your fine-tuned models
- ✅ Analyze data privately (all on-premise)
- ✅ Create slash commands for common tasks

## What's Next?

1. Get the MCP server working (5 min)
2. Test code review (2 min)
3. Try the Hermes research agent (2 min)
4. Build your diagnostic agent (5 min)
5. Create slash commands for your workflow

**Total time: ~15 minutes to full agent setup!**

---

## Files in This Directory

- `ollama-mcp-server.py` — MCP bridge to Ollama (install to ~/.claude/mcp/)
- `AGENTS_SETUP.md` — Detailed setup guide
- `example-hermes-research-agent.py` — Research agent template
- `skill-review-with-local-llm.md` — How to create code review skill

## Questions?

Check:
- `AGENTS_SETUP.md` — Full configuration details
- `/home/tp/.claude/projects/-home-tp/memory/` — Your project context
- `agents/crash-course.html` — Educational reference

**Ready? Let's build agents!** 🚀
