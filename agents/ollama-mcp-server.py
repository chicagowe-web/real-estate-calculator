#!/usr/bin/env python3
"""
MCP Server for Ollama - wraps local LLM inference
Connects Claude Code to your garage_core Ollama instance
"""

import json
import sys
from typing import Any
import urllib.request
import urllib.error

OLLAMA_URL = "http://192.168.1.200:11434"


def call_mcp(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Process MCP method calls"""

    if method == "list_tools":
        return {
            "tools": [
                {
                    "name": "code_review",
                    "description": "Review code using local LLM (fast, no API calls)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Code to review"},
                            "model": {"type": "string", "default": "qwen2.5-coder:7b"},
                            "language": {"type": "string", "description": "Programming language"}
                        },
                        "required": ["code"]
                    }
                },
                {
                    "name": "generate_code",
                    "description": "Generate code using local LLM",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "What to generate"},
                            "model": {"type": "string", "default": "qwen2.5-coder:14b"},
                            "context": {"type": "string"}
                        },
                        "required": ["prompt"]
                    }
                },
                {
                    "name": "analyze_diagnostics",
                    "description": "Analyze vehicle data with garage-ai model",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "string", "description": "Diagnostic data"},
                            "model": {"type": "string", "default": "garage-ai-v14:latest"}
                        },
                        "required": ["data"]
                    }
                },
                {
                    "name": "list_models",
                    "description": "List available models on garage_core",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }

    elif method == "call_tool":
        tool_name = params.get("name")
        tool_input = params.get("input", {})

        if tool_name == "list_models":
            result = call_ollama_api("GET", "/api/tags", {})
            models = [m["name"] for m in result.get("models", [])]
            return {"content": [{"type": "text", "text": json.dumps(models, indent=2)}]}

        elif tool_name == "code_review":
            code = tool_input.get("code", "")
            model = tool_input.get("model", "qwen2.5-coder:7b")
            language = tool_input.get("language", "python")

            prompt = f"""Review this {language} code for bugs, style, and improvements:

```{language}
{code}
```

Provide a concise review with specific improvements."""

            response = call_ollama_api("POST", "/api/generate", {
                "model": model,
                "prompt": prompt,
                "stream": False
            })

            return {"content": [{"type": "text", "text": response.get("response", "No response")}]}

        elif tool_name == "generate_code":
            prompt = tool_input.get("prompt", "")
            model = tool_input.get("model", "qwen2.5-coder:14b")
            context = tool_input.get("context", "")

            full_prompt = f"{context}\n\nGenerate: {prompt}" if context else prompt

            response = call_ollama_api("POST", "/api/generate", {
                "model": model,
                "prompt": full_prompt,
                "stream": False
            })

            return {"content": [{"type": "text", "text": response.get("response", "No response")}]}

        elif tool_name == "analyze_diagnostics":
            data = tool_input.get("data", "")
            model = tool_input.get("model", "garage-ai-v14:latest")

            prompt = f"""Analyze this vehicle diagnostic data:

{data}

Identify issues and provide severity levels."""

            response = call_ollama_api("POST", "/api/generate", {
                "model": model,
                "prompt": prompt,
                "stream": False
            })

            return {"content": [{"type": "text", "text": response.get("response", "No response")}]}

    return {"error": f"Unknown method: {method}"}


def call_ollama_api(method: str, endpoint: str, data: dict) -> dict:
    """Call Ollama API on garage_core"""
    url = f"{OLLAMA_URL}{endpoint}"

    try:
        if method == "GET":
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read())

        elif method == "POST":
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read())

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method")
            params = request.get("params", {})
            response = call_mcp(method, params)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()
