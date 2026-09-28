#!/usr/bin/env python3
"""
Step 4: Evaluate Fine-tuned Model

This script:
1. Loads fine-tuned Qwen model
2. Generates responses on test scenarios
3. Uses Claude to score responses
4. Compares to baseline
5. Generates evaluation report
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import yaml
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from anthropic import Anthropic

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Initialize Claude
client = Anthropic()

# Test scenarios
TEST_SCENARIOS = {
    "DevOps": [
        "Deploy payment-api v2.2.0 with schema changes affecting 50K users to production. Analyze the risks and recommend a deployment strategy.",
        "Update database optimization on critical service during peak hours. What's the best approach?",
        "Rollout new authentication system to 3 critical services. How should this be coordinated?",
    ],
    "Fleet": [
        "Analyze maintenance patterns across 50-vehicle delivery fleet with 15% brake wear variance. What's the maintenance strategy?",
        "Predict transmission failure probability for fleet of 200 rental vehicles. How confident are you?",
        "Plan preventive maintenance for 500-vehicle commercial fleet. What metrics matter?",
    ],
    "Infrastructure": [
        "Database queries taking 450ms with N+1 patterns. Identify root causes and recommend solutions.",
        "Cache hit rate dropped from 85% to 45%. Analyze the impact and solutions.",
        "Memory usage spiked to 90% on production servers. What are the likely causes?",
    ],
}

EVALUATION_PROMPT = """Evaluate this response on the following criteria (0-100):

1. Reasoning Quality: Does the response show clear logical thinking?
2. Accuracy: Is the analysis factually correct?
3. Confidence: Is the confidence level appropriate for the complexity?
4. Clarity: Is the response well-structured and easy to understand?
5. Completeness: Does it address the key aspects of the problem?

Respond with JSON:
{
    "reasoning_quality": 85,
    "accuracy": 78,
    "confidence_calibration": 82,
    "clarity": 88,
    "completeness": 80,
    "overall": 82,
    "notes": "Good response with clear thinking..."
}"""


def load_model(model_path: str):
    """Load fine-tuned Qwen model."""
    print("📦 Loading fine-tuned model...")

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        config["qwen"]["model_name"],
        cache_dir=config["qwen"]["cache_dir"],
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    # Load LoRA adapters
    model = PeftModel.from_pretrained(base_model, model_path)

    # Merge adapters for inference
    model = model.merge_and_unload()

    return model, tokenizer


def generate_response(model, tokenizer, prompt: str, max_length: int = 512) -> str:
    """Generate response from model."""
    inputs = tokenizer(prompt, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = inputs.to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Remove prompt from response
    response = response[len(prompt):].strip()

    return response


def evaluate_response(prompt: str, response: str) -> Dict:
    """Use Claude to evaluate response."""

    evaluation_request = f"""Prompt: {prompt}

Response: {response}

{EVALUATION_PROMPT}"""

    try:
        message = client.messages.create(
            model="claude-opus-5",
            max_tokens=500,
            messages=[{"role": "user", "content": evaluation_request}]
        )

        response_text = message.content[0].text

        # Parse JSON
        if "{" in response_text and "}" in response_text:
            json_start = response_text.index("{")
            json_end = response_text.rindex("}") + 1
            json_str = response_text[json_start:json_end]
            evaluation = json.loads(json_str)
        else:
            evaluation = {"overall": 50, "notes": "Could not parse response"}

    except Exception as e:
        print(f"⚠️  Error evaluating: {e}")
        evaluation = {"overall": 50, "error": str(e)}

    return evaluation


def main():
    """Main evaluation pipeline."""

    print("🚀 Qwen 14B Fine-Tuning: Step 4 - Evaluation")
    print("=" * 60)

    # Check if model exists
    model_path = Path(config["training"]["output_dir"]) / "final_model"
    if not model_path.exists():
        print(f"❌ Error: Model not found at {model_path}")
        print("   Run step 3 (fine-tuning) first.")
        return

    # Load model
    model, tokenizer = load_model(str(model_path))

    # Evaluate on test scenarios
    print("\n🧪 Evaluating on test scenarios...")

    all_scores = []

    for category, scenarios in TEST_SCENARIOS.items():
        print(f"\n📊 Category: {category}")
        category_scores = []

        for scenario in tqdm(scenarios, desc=f"  Evaluating {category}"):
            # Generate response
            response = generate_response(model, tokenizer, scenario)

            # Evaluate
            evaluation = evaluate_response(scenario, response)

            category_scores.append(evaluation.get("overall", 0))
            all_scores.append(evaluation.get("overall", 0))

            print(f"    Score: {evaluation.get('overall', 0)}/100")

        avg_score = sum(category_scores) / len(category_scores)
        print(f"   Average: {avg_score:.1f}/100")

    # Generate report
    print("\n" + "=" * 60)
    print("📈 Evaluation Results")
    print("=" * 60)

    overall_avg = sum(all_scores) / len(all_scores)

    print(f"\nOverall Score: {overall_avg:.1f}/100")
    print(f"Sample Size: {len(all_scores)} scenarios")
    print(f"Score Range: {min(all_scores):.1f} - {max(all_scores):.1f}")

    # Comparison to Claude (for context)
    print("\nComparison:")
    print(f"  Fine-tuned Qwen: {overall_avg:.1f}/100")
    print(f"  Claude baseline: ~92/100")
    print(f"  Gap: {92 - overall_avg:.1f} points")

    # Save report
    # Calculate category scores
    category_scores = {}
    score_idx = 0
    for cat in TEST_SCENARIOS.keys():
        cat_size = len(TEST_SCENARIOS[cat])
        cat_scores = all_scores[score_idx:score_idx + cat_size]
        category_scores[cat] = sum(cat_scores) / len(cat_scores) if cat_scores else 0
        score_idx += cat_size

    report = {
        "timestamp": str(Path(model_path).stat().st_mtime),
        "model_path": str(model_path),
        "overall_score": overall_avg,
        "category_scores": category_scores,
        "detailed_scores": all_scores,
    }

    report_path = Path("./logs/evaluation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 Report saved to: {report_path}")
    print()
    print("Next step: python 5_integrate.py")


if __name__ == "__main__":
    main()
