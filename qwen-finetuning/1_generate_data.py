#!/usr/bin/env python3
"""
Step 1: Generate Training Data using LLM

Supports multiple LLM backends:
- Claude (high quality, paid)
- DeepSeek (free API)
- Gemini (free $300 credits)
- ChatGPT (cheap, paid)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List
import yaml
from tqdm import tqdm

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Initialize LLM client based on config
backend = config.get("llm", {}).get("backend", "deepseek").lower()

if backend == "claude":
    from anthropic import Anthropic
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY environment variable not set")
        sys.exit(1)
    client = Anthropic(api_key=api_key)

elif backend == "deepseek":
    from openai import OpenAI
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        print("Get free API key at: https://platform.deepseek.com/")
        sys.exit(1)
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

elif backend == "gemini":
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Get free API key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    genai.configure(api_key=api_key)
    client = genai.GenerativeModel("gemini-pro")

elif backend == "chatgpt":
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Get API key at: https://platform.openai.com/account/api-keys")
        sys.exit(1)
    client = OpenAI(api_key=api_key)
else:
    print(f"Error: Unknown backend '{backend}'")
    sys.exit(1)

print(f"Using LLM backend: {backend.upper()}")

# Create output directory
output_dir = Path(config["data_generation"]["output_dir"])
output_dir.mkdir(parents=True, exist_ok=True)

# Domain-specific prompts
DOMAIN_PROMPTS = {
    "devops_deployment": {
        "description": "Deployment planning, risk assessment, strategy selection",
        "scenarios": [
            "Deploy payment-api v2.2.0 with schema changes affecting 50K users to production",
            "Update database query optimization on critical service during peak hours",
            "Rollout new authentication system to 3 critical services simultaneously",
            "Deploy breaking API changes to microservices with dependent services",
            "Upgrade infrastructure during holiday season with minimal team",
        ],
        "system_prompt": """You are an expert DevOps engineer and deployment strategist.
Your task is to analyze deployment scenarios and think through them carefully.

For each scenario:
1. Identify the key risks and challenges
2. Assess the overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
3. Recommend a deployment strategy (blue-green, canary, rolling, direct, A/B test)
4. Explain your reasoning step-by-step
5. List rollback triggers
6. Provide confidence in your recommendation (0-100%)

Structure your response as JSON:
{
    "scenario": "...",
    "risks": ["...", "..."],
    "risk_level": "...",
    "strategy": "...",
    "reasoning": "...",
    "rollback_triggers": ["...", "..."],
    "confidence": 85,
    "estimated_duration_seconds": 600
}"""
    },

    "fleet_management": {
        "description": "Fleet optimization, predictive maintenance, diagnostics coordination",
        "scenarios": [
            "Analyze maintenance patterns across 50-vehicle delivery fleet with 15% brake wear variance",
            "Predict transmission failure probability for fleet of 200 rental vehicles",
            "Optimize service scheduling for fleet with varying vehicle ages and mileage",
            "Detect anomalous battery performance across 100-vehicle electric fleet",
            "Plan preventive maintenance across distributed 500-vehicle commercial fleet",
        ],
        "system_prompt": """You are an expert fleet maintenance strategist and predictive analyst.
Your task is to analyze fleet scenarios and recommend optimal maintenance strategies.

For each scenario:
1. Identify patterns and anomalies in the fleet data
2. Assess risk level and priority vehicles
3. Recommend maintenance strategy (preventive, predictive, reactive)
4. Calculate expected cost savings vs. reactive approach
5. Outline implementation plan
6. Provide confidence in recommendations (0-100%)

Structure your response as JSON:
{
    "scenario": "...",
    "patterns": ["...", "..."],
    "risk_assessment": {"high": [...], "medium": [...], "low": [...]},
    "recommended_strategy": "...",
    "reasoning": "...",
    "cost_savings_percent": 35,
    "implementation_steps": ["...", "..."],
    "confidence": 78
}"""
    },

    "infrastructure_analysis": {
        "description": "Bottleneck detection, performance optimization, resource allocation",
        "scenarios": [
            "Database queries taking 450ms with N+1 patterns, affecting 5 dependent services",
            "Cache hit rate dropped from 85% to 45%, impacting API latency and cost",
            "Memory usage spike to 90% on production servers after deployment",
            "API p99 latency increased from 200ms to 2000ms with no code changes",
            "Storage I/O bottleneck causing cascade failures across 3 services",
        ],
        "system_prompt": """You are an expert infrastructure optimization engineer.
Your task is to analyze performance issues and recommend solutions.

For each scenario:
1. Identify root causes and contributing factors
2. Rank potential solutions by impact and effort
3. Recommend primary solution with alternatives
4. Estimate performance improvement (%)
5. List implementation risks
6. Provide confidence in diagnosis (0-100%)

Structure your response as JSON:
{
    "scenario": "...",
    "root_causes": ["...", "..."],
    "contributing_factors": ["...", "..."],
    "solutions": [
        {"name": "...", "impact": "35%", "effort": "medium", "risk": "low"}
    ],
    "recommended_solution": "...",
    "reasoning": "...",
    "implementation_risks": ["...", "..."],
    "confidence": 82
}"""
    },

    "complex_reasoning": {
        "description": "Multi-step reasoning, trade-off analysis, strategic decisions",
        "scenarios": [
            "Decide between cloud migration vs. on-premise scaling for 5-year horizon",
            "Evaluate microservices vs. monolith for new architecture given team expertise",
            "Compare licensing models: open-source vs. commercial SaaS for core platform",
            "Analyze cost-benefit of infrastructure automation vs. manual processes",
            "Plan team growth strategy given limited budget but high demand",
        ],
        "system_prompt": """You are a strategic technology advisor.
Your task is to analyze complex trade-offs and provide strategic recommendations.

For each scenario:
1. List all major factors and constraints
2. Identify key trade-offs (cost vs. flexibility, speed vs. reliability, etc.)
3. Analyze short-term vs. long-term implications
4. Recommend primary approach with alternatives
5. Outline success metrics and decision points
6. Provide confidence in recommendation (0-100%)

Structure your response as JSON:
{
    "scenario": "...",
    "factors": ["...", "..."],
    "constraints": ["...", "..."],
    "tradeoffs": [
        {"option1": "...", "option2": "...", "analysis": "..."}
    ],
    "recommendation": "...",
    "reasoning": "...",
    "success_metrics": ["...", "..."],
    "confidence": 75
}"""
    }
}


def generate_domain_examples(domain: str, scenarios: List[str], count: int) -> List[Dict]:
    """Generate training examples for a domain using Claude."""
    examples = []

    print(f"\n📊 Generating {count} examples for domain: {domain}")
    print(f"   System prompt: {DOMAIN_PROMPTS[domain]['description']}")

    pbar = tqdm(total=count, desc=f"  Generating {domain}")

    for i in range(count):
        # Cycle through scenarios
        scenario = scenarios[i % len(scenarios)]

        # Add variation to scenario (e.g., different scale, constraints)
        variations = ["", " with limited budget", " with tight timeline", " with team constraints"]
        variation = variations[i % len(variations)]
        prompt = scenario + variation

        # Get response from LLM backend
        try:
            if backend == "claude":
                message = client.messages.create(
                    model="claude-opus-5",
                    max_tokens=1500,
                    temperature=0.7,
                    system=DOMAIN_PROMPTS[domain]["system_prompt"],
                    messages=[
                        {
                            "role": "user",
                            "content": f"Analyze this scenario:\n\n{prompt}"
                        }
                    ]
                )
                response_text = message.content[0].text

            elif backend in ["deepseek", "chatgpt"]:
                message = client.chat.completions.create(
                    model="deepseek-chat" if backend == "deepseek" else "gpt-3.5-turbo",
                    max_tokens=1500,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "system",
                            "content": DOMAIN_PROMPTS[domain]["system_prompt"]
                        },
                        {
                            "role": "user",
                            "content": f"Analyze this scenario:\n\n{prompt}"
                        }
                    ]
                )
                response_text = message.choices[0].message.content

            elif backend == "gemini":
                response = client.generate_content(
                    f"""System: {DOMAIN_PROMPTS[domain]['system_prompt']}

User: Analyze this scenario:

{prompt}"""
                )
                response_text = response.text

            else:
                raise ValueError(f"Unknown backend: {backend}")

            # Parse response
            response_text = response_text

            # Try to parse as JSON
            try:
                # Extract JSON from response
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.index("{")
                    json_end = response_text.rindex("}") + 1
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # Fallback if not valid JSON
                    analysis = {
                        "scenario": prompt,
                        "reasoning": response_text,
                        "confidence": 65
                    }
            except json.JSONDecodeError:
                analysis = {
                    "scenario": prompt,
                    "reasoning": response_text,
                    "confidence": 65
                }

            # Create training example
            training_example = {
                "instruction": prompt,
                "domain": domain,
                "analysis": analysis,
                "reasoning": analysis.get("reasoning", response_text),
                "confidence": analysis.get("confidence", 65),
            }

            examples.append(training_example)
            pbar.update(1)

        except Exception as e:
            print(f"    ⚠️  Error generating example {i}: {e}")
            pbar.update(1)
            continue

    pbar.close()
    return examples


def main():
    """Main pipeline: Generate training data for all domains."""

    print("🚀 Qwen 14B Fine-Tuning: Step 1 - Data Generation")
    print("=" * 60)
    print(f"LLM Backend: {backend.upper()}")
    print(f"Output directory: {output_dir}")
    print(f"Total examples to generate: {sum(d['count'] for d in config['data_generation']['domains'])}")
    print()

    all_training_data = []

    # Generate examples for each domain
    for domain_config in config["data_generation"]["domains"]:
        domain_name = domain_config["name"]
        count = domain_config["count"]

        # Get scenarios for this domain
        if domain_name in DOMAIN_PROMPTS:
            scenarios = DOMAIN_PROMPTS[domain_name]["scenarios"]

            # Generate examples
            examples = generate_domain_examples(domain_name, scenarios, count)
            all_training_data.extend(examples)

            # Save domain-specific file
            domain_file = output_dir / f"{domain_name}_examples.json"
            with open(domain_file, "w") as f:
                json.dump(examples, f, indent=2)
            print(f"✅ Saved {len(examples)} examples to {domain_file}")

    # Save all training data
    all_data_file = output_dir / "all_training_data.json"
    with open(all_data_file, "w") as f:
        json.dump(all_training_data, f, indent=2)

    print()
    print("=" * 60)
    print(f"✅ Generated {len(all_training_data)} training examples")
    print(f"📁 Saved to: {output_dir}")
    print()
    print("Next step: python 2_prepare_data.py")


if __name__ == "__main__":
    main()
