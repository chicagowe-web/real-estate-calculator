# Deploy Qwen Fine-Tuning Pipeline to garage-core

## Hardware Confirmed
- **Machine:** garage-core (192.168.0.129)
- **GPU:** RTX 3080 (10 GB VRAM) ✅
- **CPU:** 8+ cores
- **Storage:** ~50GB free space required

## Quick Deploy (Copy & Run)

### 1. Copy Pipeline to garage-core
```bash
# From tp (this machine):
scp -r qwen-finetuning garage-core:/home/garage_core/

# Verify:
ssh garage-core "ls -la qwen-finetuning/"
```

### 2. Setup on garage-core
```bash
# SSH into garage-core:
ssh garage-core

# Navigate to pipeline:
cd qwen-finetuning

# Install dependencies:
pip install -r requirements.txt

# Verify GPU:
nvidia-smi
# Should show: NVIDIA RTX 3080, 10240 MB memory
```

### 3. Configure & Run
```bash
# Set Claude API key:
export CLAUDE_API_KEY="sk-..."

# Check GPU is clean:
nvidia-smi
# Should show <500MB used before training starts

# Step 1: Generate training data (2-3 hours)
python 1_generate_data.py

# Step 2: Prepare datasets (5-10 minutes)
python 2_prepare_data.py

# Step 3: Fine-tune (6 hours per epoch × 3 = 18 hours)
python 3_finetune.py

# Step 4: Evaluate (30 minutes)
python 4_evaluate.py

# Step 5: Integrate with Ollama (10 minutes)
python 5_integrate.py
```

### 4. Long-Running Training (Detach & Monitor)

To run training without blocking your terminal:

```bash
# Option A: Use screen (preferred for long training)
screen -S qwen-training
cd qwen-finetuning
python 3_finetune.py
# Press Ctrl+A then D to detach

# Reattach later:
screen -r qwen-training

# Option B: Use nohup for non-interactive
nohup python 3_finetune.py > training.log 2>&1 &

# Monitor:
tail -f training.log
```

### 5. Monitor Training Progress

From tp or another terminal:
```bash
# Check GPU usage in real-time:
ssh garage-core "watch -n 2 nvidia-smi"

# Check training logs:
ssh garage-core "tail -f qwen-finetuning/logs/training.log"

# Check model directory:
ssh garage-core "du -sh qwen-finetuning/outputs/qwen-14b-reasoner/"
```

## Expected Timeline

| Step | Time | Output |
|------|------|--------|
| 1. Generate Data | 2-3 hrs | `data/generated/all_training_data.json` (2000 examples) |
| 2. Prepare Data | 5-10 min | `data/prepared/{train,val}_dataset` |
| 3. Fine-tune | 18 hrs total | `outputs/qwen-14b-reasoner/final_model` |
| 4. Evaluate | 30 min | `logs/evaluation_report.json` |
| 5. Integrate | 10 min | Modelfile + qwen_reasoner_client.py |

**Total: ~20-22 hours (runs mostly unattended)**

## GPU Memory Profile

RTX 3080 (10GB) breakdown:
```
Model State:        ~3.2 GB
LoRA Adapters:      ~50 MB
Optimizer States:   ~800 MB
Batch/Gradients:    ~1.0 GB
Overhead:           ~500 MB
━━━━━━━━━━━━━━━━━━━━━━━━━
Total Used:         ~5.5 GB (leaving 4.5GB margin)
```

## If Training Fails

### OOM (Out of Memory) Error
```bash
# Reduce batch size in config.yaml:
per_device_train_batch_size: 2  # Was 4
per_device_eval_batch_size: 4   # Was 8

# Re-run step 3:
python 3_prepare_data.py
python 3_finetune.py
```

### CUDA Error
```bash
# Restart GPU:
ssh garage-core "sudo nvidia-smi -pm 1 && sleep 5"

# Retry training:
python 3_finetune.py
```

### Checkpoint Recovery
If training interrupted, resume from checkpoint:
```bash
# Check available checkpoints:
ls -la outputs/qwen-14b-reasoner/checkpoint-*

# Edit training arguments to resume:
# In 3_finetune.py, TrainingArguments will auto-resume from latest checkpoint
python 3_finetune.py
```

## Next: Integrate with DevOps Assistant

Once training completes:

1. Test locally on garage-core:
   ```bash
   python qwen_reasoner_client.py
   # Should print: ✅ Model working!
   ```

2. Deploy Ollama model:
   ```bash
   bash deploy.sh
   ```

3. Use in DevOps Assistant:
   ```python
   from qwen_reasoner_client import QwenReasonerClient
   
   client = QwenReasonerClient(ollama_url="http://localhost:11434")
   result = client.generate("Analyze deployment risk for...")
   ```

## Post-Training: Copy Results Back

```bash
# From tp:
scp -r garage-core:qwen-finetuning/outputs ./qwen-results/
scp -r garage-core:qwen-finetuning/logs ./qwen-results/
scp garage-core:qwen-finetuning/evaluation_report.json ./qwen-results/
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH timeout | Increase SSH timeout: `ssh -o ConnectTimeout=60 garage-core` |
| Slow data transfer | Use rsync instead: `rsync -avz qwen-finetuning garage-core:/home/garage_core/` |
| Model won't load | Ensure correct model name: `Qwen/Qwen1.5-14B` in config.yaml |
| Ollama not running | Start: `ollama serve` in separate terminal on garage-core |
| Training takes too long | Reduce `num_epochs` from 3 to 1 in config.yaml for testing |

---

**Ready to train?** ✅ Follow steps 1-5 above and the pipeline will complete in ~20 hours on RTX 3080.
