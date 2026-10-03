# Skill: Review Code with Local LLM

**Name:** code-review-local  
**Type:** Custom Skill for Claude Code  
**Model:** Uses your local Ollama (qwen2.5-coder:7b for speed)  
**When to use:** Quick code reviews without cloud API calls

## How to install:

1. Copy `ollama-mcp-server.py` to `~/.claude/mcp/` and make it executable:
```bash
mkdir -p ~/.claude/mcp
cp agents/ollama-mcp-server.py ~/.claude/mcp/
chmod +x ~/.claude/mcp/ollama-mcp-server.py
```

2. Add to `.claude/settings.json`:
```json
{
  "mcp": {
    "ollama": {
      "command": "python3",
      "args": ["~/.claude/mcp/ollama-mcp-server.py"]
    }
  }
}
```

3. Restart Claude Code

## Usage:

```bash
/code-review-local <file-or-branch>
```

This will:
- Extract code from your file or git diff
- Send it to local Ollama (no cloud)
- Get fast feedback using qwen2.5-coder
- Show results in Claude Code terminal

## What models are available:

- `qwen2.5-coder:7b` — Fast, 7B params, good for quick reviews
- `qwen2.5-coder:14b` — Better quality, 14B params, slower
- `deepseek-coder:latest` — Tiny (1B), ultra-fast, good for simple issues
- `garage-ai-v14:latest` — Your custom model, best for automotive code

## Example workflow:

```
You: /code-review-local src/vehicle_agent.py
Claude: Using local LLM (qwen2.5-coder:7b)...
[Reviews your code with Ollama]
Results: Found 2 potential issues...
```

## Why use local LLM for code review?

✅ **Speed** — No API latency, instant results  
✅ **Privacy** — Code never leaves your network  
✅ **Cost** — Free after initial model download  
✅ **Offline** — Works without internet  
✅ **Specialized** — Use garage-ai-v14 for automotive code  

## Alternative: Cloud review

For more thorough reviews, still use Claude's `/code-review` command — it uses Claude Opus for deeper analysis and is better for complex logic.

**Recommendation:** Use local LLM for quick iteration (5-10 min reviews), Claude Opus for deep reviews (complex PRs, before merging to main).
