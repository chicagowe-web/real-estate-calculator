#!/usr/bin/env python3
"""
Step 2: Prepare Data for Fine-tuning

This script:
1. Loads generated examples from Step 1
2. Formats data for LLM fine-tuning
3. Creates train/val splits
4. Tokenizes examples
5. Saves prepared datasets
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import yaml
import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer
from tqdm import tqdm

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Paths
data_dir = Path(config["data_generation"]["output_dir"])
output_dir = Path(config["data_preparation"].get("output_dir", "./data/prepared"))
output_dir.mkdir(parents=True, exist_ok=True)

# Load tokenizer
print("📦 Loading Qwen tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    config["qwen"]["model_name"],
    cache_dir=config["qwen"]["cache_dir"],
    trust_remote_code=True
)

# Set pad token if not set
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


def format_training_example(example: Dict) -> Dict:
    """Format a raw example into training format."""

    instruction = example.get("instruction", "")
    reasoning = example.get("reasoning", "")
    analysis = example.get("analysis", {})

    # Create prompt-completion format
    prompt = f"""Analyze the following scenario carefully and provide your reasoning:

{instruction}

Think through this step-by-step:"""

    completion = f""" {reasoning}

Confidence: {example.get('confidence', 75)}/100"""

    # Combine into single text
    text = prompt + completion

    return {
        "text": text,
        "instruction": instruction,
        "domain": example.get("domain", "general"),
        "confidence": example.get("confidence", 75),
    }


def prepare_data():
    """Load, format, and split data."""

    print("🚀 Qwen 14B Fine-Tuning: Step 2 - Data Preparation")
    print("=" * 60)

    # Load all training data
    print("📂 Loading generated examples...")
    all_data_file = data_dir / "all_training_data.json"

    if not all_data_file.exists():
        print(f"❌ Error: {all_data_file} not found. Run step 1 first.")
        return

    with open(all_data_file, "r") as f:
        raw_examples = json.load(f)

    print(f"   Loaded {len(raw_examples)} examples")

    # Format examples
    print("🔄 Formatting examples...")
    formatted_examples = []
    for example in tqdm(raw_examples, desc="  Formatting"):
        formatted = format_training_example(example)
        formatted_examples.append(formatted)

    # Create train/val split
    print("📊 Splitting data...")
    split_ratio = config["data_preparation"]["train_split"]
    n_train = int(len(formatted_examples) * split_ratio)

    # Shuffle first
    indices = np.random.permutation(len(formatted_examples))

    train_examples = [formatted_examples[i] for i in indices[:n_train]]
    val_examples = [formatted_examples[i] for i in indices[n_train:]]

    print(f"   Train: {len(train_examples)} examples")
    print(f"   Val: {len(val_examples)} examples")

    # Tokenize
    print("🔤 Tokenizing examples...")

    def tokenize_function(examples):
        """Tokenize function for dataset mapping."""
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            max_length=config["data_preparation"]["max_length"],
            padding="max_length"
        )

        # For causal language modeling, labels = input_ids
        tokenized["labels"] = tokenized["input_ids"]

        return tokenized

    # Create HuggingFace datasets
    train_dataset = Dataset.from_dict({
        "text": [ex["text"] for ex in train_examples],
        "instruction": [ex["instruction"] for ex in train_examples],
        "domain": [ex["domain"] for ex in train_examples],
    })

    val_dataset = Dataset.from_dict({
        "text": [ex["text"] for ex in val_examples],
        "instruction": [ex["instruction"] for ex in val_examples],
        "domain": [ex["domain"] for ex in val_examples],
    })

    # Tokenize datasets
    print("   Tokenizing training set...")
    train_dataset = train_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text", "instruction", "domain"],
        desc="  Train",
    )

    print("   Tokenizing validation set...")
    val_dataset = val_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text", "instruction", "domain"],
        desc="  Val",
    )

    # Save datasets
    print("💾 Saving prepared datasets...")
    train_path = output_dir / "train_dataset"
    val_path = output_dir / "val_dataset"

    train_dataset.save_to_disk(str(train_path))
    val_dataset.save_to_disk(str(val_path))

    print(f"   Train: {train_path}")
    print(f"   Val: {val_path}")

    # Save statistics
    stats = {
        "total_examples": len(formatted_examples),
        "train_size": len(train_dataset),
        "val_size": len(val_dataset),
        "max_length": config["data_preparation"]["max_length"],
        "tokenizer": config["qwen"]["model_name"],
    }

    stats_file = output_dir / "stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

    print()
    print("=" * 60)
    print("✅ Data preparation complete")
    print(f"   Statistics saved to {stats_file}")
    print()
    print("Next step: python 3_finetune.py")


if __name__ == "__main__":
    prepare_data()
