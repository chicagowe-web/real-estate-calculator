#!/usr/bin/env python3
"""
Step 3: Fine-tune Qwen 14B using LoRA

This script:
1. Loads Qwen 14B model
2. Applies LoRA adapters for efficient fine-tuning
3. Trains on prepared dataset
4. Saves fine-tuned model

GPU Memory: ~8GB (RTX 3080)
Time: ~6 hours per epoch
"""

import os
import sys
from pathlib import Path
import yaml
import torch
from datasets import load_from_disk
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datetime import datetime

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Check CUDA availability
if not torch.cuda.is_available():
    print("❌ Error: CUDA not available. GPU required for fine-tuning.")
    sys.exit(1)

print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")


def load_datasets():
    """Load prepared training and validation datasets."""
    print("📂 Loading prepared datasets...")

    data_dir = Path("./data/prepared")

    train_dataset = load_from_disk(str(data_dir / "train_dataset"))
    val_dataset = load_from_disk(str(data_dir / "val_dataset"))

    print(f"   Train: {len(train_dataset)} examples")
    print(f"   Val: {len(val_dataset)} examples")

    return train_dataset, val_dataset


def setup_model_and_tokenizer():
    """Load Qwen model and set up LoRA."""
    print("📦 Loading Qwen 14B model...")

    model_name = config["qwen"]["model_name"]
    cache_dir = config["qwen"]["cache_dir"]

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with 8-bit quantization for memory efficiency
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        device_map="auto",
        torch_dtype=torch.float16,
        load_in_8bit=True,
        trust_remote_code=True,
    )

    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    print("🔧 Applying LoRA adapters...")

    # Configure LoRA
    lora_config = LoraConfig(
        r=config["lora"]["r"],
        lora_alpha=config["lora"]["lora_alpha"],
        target_modules=config["lora"]["target_modules"],
        lora_dropout=config["lora"]["lora_dropout"],
        bias=config["lora"]["bias"],
        task_type=config["lora"]["task_type"],
    )

    # Apply LoRA to model
    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    print(f"   Trainable params: {trainable_params:,}")
    print(f"   Total params: {total_params:,}")
    print(f"   % Trainable: {trainable_params / total_params * 100:.2f}%")

    return model, tokenizer


def setup_training_args():
    """Configure training arguments."""
    training_args = TrainingArguments(
        output_dir=config["training"]["output_dir"],
        num_train_epochs=config["training"]["num_epochs"],
        per_device_train_batch_size=config["training"]["per_device_train_batch_size"],
        per_device_eval_batch_size=config["training"]["per_device_eval_batch_size"],
        learning_rate=config["training"]["learning_rate"],
        warmup_ratio=config["training"]["warmup_ratio"],
        weight_decay=config["training"]["weight_decay"],
        logging_steps=config["training"]["logging_steps"],
        save_strategy=config["training"]["save_strategy"],
        save_total_limit=config["training"]["save_total_limit"],
        seed=config["training"]["seed"],
        fp16=True,  # Use mixed precision
        logging_dir="./logs",
        report_to="wandb" if config["logging"]["wandb"]["enabled"] else [],
        run_name=f"qwen-14b-reasoner-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )

    return training_args


def main():
    """Main fine-tuning pipeline."""

    print("🚀 Qwen 14B Fine-Tuning: Step 3 - Fine-tuning")
    print("=" * 60)
    print(f"Model: {config['qwen']['model_name']}")
    print(f"Epochs: {config['training']['num_epochs']}")
    print(f"Batch size: {config['training']['per_device_train_batch_size']}")
    print(f"Learning rate: {config['training']['learning_rate']}")
    print()

    # Load data
    train_dataset, val_dataset = load_datasets()

    # Setup model
    model, tokenizer = setup_model_and_tokenizer()

    # Setup training
    training_args = setup_training_args()

    # Data collator for language modeling
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal language modeling (not masked)
    )

    print("🎯 Starting training...")
    print(f"   Output: {training_args.output_dir}")
    print()

    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )

    # Train
    train_result = trainer.train()

    # Save final model
    print("\n💾 Saving fine-tuned model...")
    model_path = Path(config["training"]["output_dir"]) / "final_model"
    model_path.mkdir(parents=True, exist_ok=True)

    # Save model and tokenizer
    trainer.model.save_pretrained(str(model_path))
    tokenizer.save_pretrained(str(model_path))

    # Save training results
    results = {
        "training_loss": train_result.training_loss,
        "epochs": config["training"]["num_epochs"],
        "model_path": str(model_path),
        "timestamp": datetime.now().isoformat(),
    }

    print()
    print("=" * 60)
    print("✅ Fine-tuning complete")
    print(f"   Model saved to: {model_path}")
    print(f"   Training loss: {results['training_loss']:.4f}")
    print()
    print("Next step: python 4_evaluate.py")


if __name__ == "__main__":
    main()
