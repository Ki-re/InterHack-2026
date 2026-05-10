# Train New Large Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `IA/train_new.py` as a larger checkpointed PyTorch trainer for `IA/dataset_modelo.csv`.

**Architecture:** Create a standalone training script that keeps the original preprocessing contract, swaps the model for a configurable deeper MLP, and saves periodic, best, and final checkpoints. Validation and test report both loss components and requested accuracy-style metrics.

**Tech Stack:** Python, pandas, NumPy, PyTorch, Git.

---

## File Structure

- Create: `IA/train_new.py` as the new training entrypoint.
- Modify: `.gitignore` to ignore generated model checkpoints.
- Reference: `IA/train.py` for existing targets, leakage columns, preprocessing, and loss shape.
- Reference: `docs/superpowers/specs/2026-05-09-train-new-large-model-design.md` for approved behavior.

### Task 1: Add checkpoint ignores

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add checkpoint ignore patterns**

Append these lines near the project runtime section:

```gitignore
/IA/checkpoints*/
/IA/*.pt
```

- [ ] **Step 2: Verify ignore syntax**

Run: `git diff -- .gitignore`

Expected: diff shows only the two checkpoint patterns.

### Task 2: Create `IA/train_new.py`

**Files:**
- Create: `IA/train_new.py`

- [ ] **Step 1: Copy stable dataset constants and preprocessing**

Use the same target columns, leakage columns, split, one-hot encoding, NaN handling, and train-only standardization from `IA/train.py`.

- [ ] **Step 2: Implement larger configurable model**

Define `LargePurchaseModel` with hidden sizes parsed from `--hidden-sizes`, defaulting to `512,256,128,64`, with `Linear`, `BatchNorm1d`, `SiLU`, and `Dropout` blocks.

- [ ] **Step 3: Implement losses and requested metrics**

Keep the original loss family and add:

```python
acc_recompra = ((pred[:, 0] >= 0.5).float() == target[:, 0].round()).float().mean()
acc_dias_pm3 = (torch.abs(pred[:, 1] - target[:, 1]) <= args.metric_days_tolerance).float().mean()
acc_potencial_pm02 = (torch.abs(pred[:, 2] - target[:, 2]) <= args.metric_potential_tolerance).float().mean()
```

- [ ] **Step 4: Implement training loop and checkpointing**

Use `AdamW`, `ReduceLROnPlateau`, gradient clipping, optional AMP on CUDA, periodic checkpoints, `best_model.pt`, and `last_model.pt`.

- [ ] **Step 5: Save reproducibility metadata**

Each checkpoint must include model config, feature names, target columns, train means/stds, optimizer state, scheduler state, epoch, and metrics.

### Task 3: Validate

**Files:**
- Verify: `IA/train_new.py`

- [ ] **Step 1: Compile script**

Run: `python -m py_compile IA/train_new.py`

Expected: command exits successfully.

- [ ] **Step 2: Run a short smoke train if dependencies are available**

Run:

```powershell
python IA\train_new.py --csv IA\dataset_modelo.csv --epochs 1 --batch-size 4096 --sample-rows 20000 --checkpoint-dir IA\checkpoints_smoke --checkpoint-every 1
```

Expected: script prints validation metrics including `val_acc_recompra`, `val_acc_dias_pm3`, and `val_acc_potencial_pm02`, then saves checkpoints.

### Task 4: Provide long training command

**Files:**
- No file changes.

- [ ] **Step 1: Give GPU-oriented command**

Return a PowerShell command using `--epochs 300`, `--batch-size 2048`, checkpointing every `10` epochs, `--amp`, and the large default model.
