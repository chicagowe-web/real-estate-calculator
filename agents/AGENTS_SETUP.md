# Agent Setup Guide - Local LLM + Custom Agents

Your infrastructure is ready. Here's how to set up agents for your workspace.

## Architecture

```
Your Laptop (Control Plane)
├─ Claude Code (IDE + agent runner)
└─ MCP Client
    ↓ talks to garage_core (RTX 3080)
    └─ Ollama Server (local LLMs)
       ├─ qwen2.5-coder (fast coding LLM)
       ├─ deepseek-coder (ultra-compact)
       └─ garage-ai-v14 (your custom model)
```

## Step 1: Set up MCP Server

The MCP server is the bridge between Claude Code and Ollama.

### Install MCP Server

```bash
mkdir -p ~/.claude/mcp
cp agents/ollama-mcp-server.py ~/.claude/mcp/
chmod +x ~/.claude/mcp/ollama-mcp-server.py
```

### Configure in Claude Code

Edit `~/.claude/settings.json`:

```json
{
  "mcp": {
    "ollama-local": {
      "command": "python3",
      "args": ["/Users/<your-user>/.claude/mcp/ollama-mcp-server.py"]
    }
  }
}
```

Replace `/Users/<your-user>` with your actual home directory path.

### Verify Connection

Test from Claude Code:
```bash
curl http://192.168.1.200:11434/api/tags
```

You should see all your Ollama models listed.

---

## Step 2: Create Slash Commands (Skills)

Slash commands are shortcuts you type to trigger agents. Create a skill file:

### Example: `/code-review-local`

Create `~/.claude/skills/code-review-local.md`:

```markdown
# /code-review-local

Review code using local LLM (qwen2.5-coder)

## Task

Review the current diff or specified file using the local Ollama server.

## Workflow

1. Get the code diff
2. Send to local LLM via MCP
3. Return findings
4. Optionally fix issues

## Instructions

Use the `ollama-local` MCP resource to call the `code_review` tool.
```

Then in Claude Code, type:
```
/code-review-local src/my_file.py
```

---

## Step 3: Create Background Agents

Background agents run on their own schedule or event-triggered. Use the `/loop` command:

### Example 1: Monitor Vehicle Diagnostics (every 5 minutes)

```bash
/loop 5m

Analyze latest vehicle diagnostic data from /data/diagnostics/latest.json.
If any error codes are detected, log them to the alert system.
Use the garage-ai-v14 model via MCP for analysis.
```

### Example 2: Analyze Research on Hermes OS (once)

```bash
Research agent: Find latest YouTube videos on Hermes OS.
Analyze them for:
- Performance improvements
- New features
- Community feedback
- Integration opportunities with your system

Store findings in /data/research/hermes-analysis.md
```

### Example 3: Code Quality Check (on every commit)

Hook configuration (in `.claude/settings.json`):

```json
{
  "hooks": {
    "post-commit": "echo 'Running code quality check...' && /code-review-local HEAD~1..HEAD"
  }
}
```

---

## Step 4: Your Agent Fleet

Here's what you should set up:

### 🚗 Diagnostic Agent
**Purpose:** Monitor vehicle health  
**Model:** garage-ai-v14  
**Schedule:** Every 5 minutes  
**Action:** Analyze CAN/OBD data, alert on issues

### 🧠 Code Review Agent
**Purpose:** Review PRs and diffs  
**Model:** qwen2.5-coder:14b  
**Schedule:** On commit  
**Action:** Find bugs, suggest improvements

### 📺 Research Agent
**Purpose:** Analyze YouTube, forums, docs  
**Model:** Claude Sonnet (for web research) + local summaries  
**Schedule:** Daily  
**Action:** Find Hermes OS improvements, track tech trends

### 🚀 Deployment Agent
**Purpose:** Deploy to canfd/garage-core  
**Model:** qwen2.5-coder:7b (for script generation)  
**Schedule:** On demand  
**Action:** Build, test, deploy

### 📊 Monitoring Agent
**Purpose:** Track system health  
**Model:** None (just data analysis)  
**Schedule:** Continuous  
**Action:** Alert on anomalies

---

## Step 5: Test Your Setup

### Test 1: Can Claude Code reach Ollama?

```bash
curl -s http://192.168.1.200:11434/api/tags | jq '.models[].name'
```

Expected output: List of your models

### Test 2: Test MCP server directly

```bash
echo '{"method":"list_tools","params":{}}' | python3 ~/.claude/mcp/ollama-mcp-server.py
```

Expected output: JSON with available tools

### Test 3: Test code review

```bash
echo '{"method":"call_tool","params":{"name":"code_review","input":{"code":"x=1+1"}}}' | python3 ~/.claude/mcp/ollama-mcp-server.py
```

Expected output: Review of the code snippet

---

## Step 6: Create Your First Agent

Let's start with the code review agent. Create `~/.claude/agents/code-review-local.sh`:

```bash
#!/bin/bash

# Review code with local LLM
# Usage: /code-review-local src/file.py

FILE=$1
MODEL=${2:-qwen2.5-coder:7b}

echo "📍 Reviewing $FILE with $MODEL..."

# Get the code
CODE=$(cat "$FILE")

# Send to local LLM via curl (for testing)
curl -s http://192.168.1.200:11434/api/generate \
  -d "{
    \"model\": \"$MODEL\",
    \"prompt\": \"Review this code and suggest improvements:\n\n\`\`\`\n$CODE\n\`\`\`\",
    \"stream\": false
  }" | jq -r '.response'
```

---

## Quick Reference: Available Models

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `deepseek-coder:latest` | 776MB | ⚡⚡⚡ | Quick reviews |
| `qwen2.5-coder:7b` | 4.7GB | ⚡⚡ | Fast iteration |
| `qwen2.5-coder:14b` | 9GB | ⚡ | Quality reviews |
| `garage-ai-v14:latest` | 4.7GB | ⚡⚡ | Automotive code |
| `hermes3:latest` | 4.7GB | ⚡⚡ | General reasoning |

---

## Next Steps

1. ✅ Set up MCP server
2. ✅ Test connectivity to Ollama
3. ✅ Create first slash command
4. ✅ Set up monitoring agent for vehicle diagnostics
5. ✅ Create research agent for Hermes OS analysis
6. ✅ Integrate with GitHub for auto-review on PRs

## Troubleshooting

**"Connection refused to 192.168.1.200:11434"**
- Check: `ssh garage-core "systemctl status ollama"`
- Verify network: `ping 192.168.1.200`

**"Model not found"**
- List models: `ssh garage-core "ollama list"`
- Pull model: `ssh garage-core "ollama pull qwen2.5-coder:14b"`

**MCP server not responding**
- Test: `echo '{"method":"list_tools","params":{}}' | python3 ~/.claude/mcp/ollama-mcp-server.py`
- Check Python version: `python3 --version` (needs 3.8+)

---

**You're ready to build your agent ecosystem!** 🚀
