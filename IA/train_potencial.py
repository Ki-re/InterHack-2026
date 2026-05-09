"""Train a dedicated regression model for target_potencial_cliente.

Key differences from the combined model:
  - Per-sample inverse-frequency bucket-weighted MSE loss
    to counter the heavy skew toward negative values (69% in {muy_neg, neg})
  - Tanh output bounded to [-1, 1]

Target distribution (training data):
  muy_neg  [-1.0, -0.5)  ~39%
  neg      [-0.5, -0.05) ~30%
  estable  [-0.05, 0.05)  ~8%
  pos      [0.05, 0.5)   ~11%
  muy_pos  [0.5, 1.0]    ~12%

Usage:
    conda run -n interhack python IA/train_potencial.py \
        --csv IA/dataset_modelo.csv \
        --epochs 250 --batch-size 2048 --lr 5e-4 \
        --weight-decay 5e-4 --hidden-sizes "512,256,128,64" \
        --dropout 0.25 --checkpoint-dir IA/checkpoints_potencial \
        --checkpoint-every 10 --grad-clip 1.0 --device auto --amp
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from ia_utils import (
    build_features,
    build_trunk,
    describe_device,
    finalize_totals,
    get_device,
    make_dataloader,
    make_json_safe_config,
    parse_hidden_sizes,
    save_checkpoint,
    split_dataframe,
    update_totals,
)

MODEL_TARGET = "target_potencial_cliente"

# Bucket boundaries (same as print_target_analysis in ia_utils)
BUCKET_BINS = torch.tensor([-0.5, -0.05, 0.05, 0.5])  # 4 boundaries → 5 buckets
N_BUCKETS = 5


class PotencialModel(nn.Module):
    """Regression model for target_potencial_cliente ∈ [-1, 1]."""

    def __init__(self, input_size: int, hidden_sizes: list[int], dropout: float = 0.25) -> None:
        super().__init__()
        self.trunk, out_features = build_trunk(input_size, hidden_sizes, dropout)
        self.head = nn.Linear(out_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.head(self.trunk(x)).squeeze(1))


def compute_bucket_weights(targets: torch.Tensor) -> torch.Tensor:
    """Compute per-sample inverse-frequency weights based on 5 value buckets.

    Weight for bucket b = total_samples / (N_BUCKETS * count_b).
    This ensures each bucket contributes equally to the total loss.
    """
    bucket_idx = torch.bucketize(targets, BUCKET_BINS.to(targets.device))
    counts = torch.bincount(bucket_idx, minlength=N_BUCKETS).float()
    # Avoid div-by-zero for empty buckets
    counts = counts.clamp(min=1)
    weights_per_bucket = targets.size(0) / (N_BUCKETS * counts)
    # Normalize so mean weight == 1 (keeps loss scale comparable)
    weights_per_bucket = weights_per_bucket / weights_per_bucket.mean()
    return weights_per_bucket[bucket_idx]


def compute_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    sample_weights: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Weighted MSE loss."""
    sq_err = (pred - target) ** 2
    loss = (sample_weights * sq_err).mean()
    unweighted_mse = sq_err.mean()
    return loss, {
        "loss": float(loss.detach().cpu()),
        "mse_potencial": float(unweighted_mse.detach().cpu()),
    }


@torch.no_grad()
def compute_metrics(
    pred: torch.Tensor,
    target: torch.Tensor,
    potential_tolerance: float = 0.2,
) -> dict[str, float]:
    acc_pm02 = (torch.abs(pred - target) <= potential_tolerance).float().mean()
    mae = torch.abs(pred - target).mean()

    # Per-bucket accuracy (informational)
    bucket_idx = torch.bucketize(target, BUCKET_BINS.to(target.device))
    bucket_names = ["muy_neg", "neg", "estable", "pos", "muy_pos"]
    bucket_accs: dict[str, float] = {}
    for b, name in enumerate(bucket_names):
        mask = bucket_idx == b
        if mask.sum() > 0:
            bucket_accs[f"acc_pm02_{name}"] = float(
                (torch.abs(pred[mask] - target[mask]) <= potential_tolerance).float().mean().cpu()
            )

    return {
        "acc_potencial_pm02": float(acc_pm02.cpu()),
        "mae_potencial": float(mae.cpu()),
        **bucket_accs,
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: Any,
    device: torch.device,
    potential_tolerance: float,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_samples = 0
    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device, non_blocking=True)
        y_batch = y_batch.to(device, non_blocking=True)
        pred = model(x_batch)
        weights = compute_bucket_weights(y_batch)
        _, loss_m = compute_loss(pred, y_batch, weights)
        acc_m = compute_metrics(pred, y_batch, potential_tolerance)
        update_totals(totals, {**loss_m, **acc_m}, x_batch.size(0))
        n_samples += x_batch.size(0)
    return finalize_totals(totals, n_samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train regression model for target_potencial_cliente")
    parser.add_argument("--csv", type=Path, default=Path("IA/dataset_modelo.csv"))
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--hidden-sizes", type=parse_hidden_sizes, default=parse_hidden_sizes("512,256,128,64"))
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("IA/checkpoints_potencial"))
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--metric-potential-tolerance", type=float, default=0.2)
    parser.add_argument("--sample-rows", type=int, default=0)
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=[MODEL_TARGET]).reset_index(drop=True)
    if args.sample_rows > 0 and args.sample_rows < len(df):
        df = df.sample(n=args.sample_rows, random_state=args.seed).reset_index(drop=True)
        print(f"Using sampled dataset: rows={len(df):,}")

    print(f"Loaded {args.csv}: {len(df):,} rows")
    print(f"\ntarget_potencial_cliente stats:")
    print(df[MODEL_TARGET].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    buckets = pd.cut(
        df[MODEL_TARGET],
        bins=[-1.01, -0.5, -0.05, 0.05, 0.5, 1.01],
        labels=["muy_neg", "neg", "estable", "pos", "muy_pos"],
    )
    print("\nBucket distribution:")
    print(buckets.value_counts().sort_index())

    train_df, val_df, test_df = split_dataframe(df, seed=args.seed)
    print(f"\nSplit: train={len(train_df):,} val={len(val_df):,} test={len(test_df):,}")

    x_train, x_val, x_test, feature_names, feature_means, feature_stds = build_features(
        train_df, val_df, test_df
    )
    y_train = torch.tensor(train_df[MODEL_TARGET].clip(-1, 1).to_numpy(dtype=np.float32))
    y_val = torch.tensor(val_df[MODEL_TARGET].clip(-1, 1).to_numpy(dtype=np.float32))
    y_test = torch.tensor(test_df[MODEL_TARGET].clip(-1, 1).to_numpy(dtype=np.float32))

    print(f"\nInput size: {x_train.shape[1]}  Hidden sizes: {args.hidden_sizes}")

    # Print bucket weights so user can verify they look reasonable
    w = compute_bucket_weights(y_train)
    print(f"Sample weight stats — min: {w.min():.3f}  max: {w.max():.3f}  mean: {w.mean():.3f}")

    device = get_device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    pin_memory = device.type == "cuda"
    BUCKET_BINS.to(device)  # pre-move for GPU use in loss

    train_loader = make_dataloader(x_train, y_train, args.batch_size, shuffle=True,
                                   num_workers=args.num_workers, pin_memory=pin_memory)
    val_loader = make_dataloader(x_val, y_val, args.batch_size,
                                 num_workers=args.num_workers, pin_memory=pin_memory)
    test_loader = make_dataloader(x_test, y_test, args.batch_size,
                                  num_workers=args.num_workers, pin_memory=pin_memory)

    model = PotencialModel(x_train.shape[1], args.hidden_sizes, args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=10, min_lr=1e-6
    )

    amp_enabled = args.amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    config = make_json_safe_config(args, args.hidden_sizes)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (args.checkpoint_dir / "run_config.json").write_text(
        __import__("json").dumps(config, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"Device: {describe_device(device)}  AMP: {amp_enabled}")
    print(f"Checkpoint dir: {args.checkpoint_dir}")

    best_val_loss = float("inf")
    best_epoch = 0
    last_train_m: dict[str, float] = {}
    last_val_m: dict[str, float] = {}

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_totals: dict[str, float] = {}
        n_train = 0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda", enabled=amp_enabled):
                pred = model(x_batch)
                weights = compute_bucket_weights(y_batch)
                loss, loss_m = compute_loss(pred, y_batch, weights)
            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            update_totals(train_totals, loss_m, x_batch.size(0))
            n_train += x_batch.size(0)

        train_m = finalize_totals(train_totals, n_train)
        val_m = evaluate(model, val_loader, device, args.metric_potential_tolerance)
        scheduler.step(val_m["loss"])
        current_lr = optimizer.param_groups[0]["lr"]
        last_train_m, last_val_m = train_m, val_m

        improved = val_m["loss"] < best_val_loss
        if improved:
            best_val_loss = val_m["loss"]
            best_epoch = epoch
            save_checkpoint(
                args.checkpoint_dir / "best_model.pt",
                model=model, optimizer=optimizer, scheduler=scheduler,
                epoch=epoch, train_metrics=train_m, val_metrics=val_m,
                feature_names=feature_names, feature_means=feature_means,
                feature_stds=feature_stds, config=config,
                best_val_loss=best_val_loss, target_cols=[MODEL_TARGET],
            )

        if args.checkpoint_every > 0 and epoch % args.checkpoint_every == 0:
            save_checkpoint(
                args.checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.pt",
                model=model, optimizer=optimizer, scheduler=scheduler,
                epoch=epoch, train_metrics=train_m, val_metrics=val_m,
                feature_names=feature_names, feature_means=feature_means,
                feature_stds=feature_stds, config=config,
                best_val_loss=best_val_loss, target_cols=[MODEL_TARGET],
            )

        # Print per-bucket accs every 10 epochs to track per-class progress
        bucket_str = ""
        if epoch % 10 == 0:
            b_accs = {k: v for k, v in val_m.items() if k.startswith("acc_pm02_")}
            bucket_str = " " + " ".join(f"{k.split('_')[-1]}={v:.3f}" for k, v in b_accs.items())

        print(
            f"Epoch {epoch:03d} lr={current_lr:.2e} "
            f"train_loss={train_m['loss']:.4f} val_loss={val_m['loss']:.4f} "
            f"val_mse={val_m['mse_potencial']:.4f} "
            f"val_acc_pm02={val_m['acc_potencial_pm02']:.4f} "
            f"val_mae={val_m['mae_potencial']:.4f} "
            f"best_epoch={best_epoch:03d}"
            f"{bucket_str}"
        )

    test_m = evaluate(model, test_loader, device, args.metric_potential_tolerance)
    print("\n=== Test metrics ===")
    for key, value in test_m.items():
        print(f"  {key}: {value:.4f}")

    save_checkpoint(
        args.checkpoint_dir / "last_model.pt",
        model=model, optimizer=optimizer, scheduler=scheduler,
        epoch=args.epochs, train_metrics=last_train_m, val_metrics=last_val_m,
        test_metrics=test_m, feature_names=feature_names,
        feature_means=feature_means, feature_stds=feature_stds,
        config=config, best_val_loss=best_val_loss, target_cols=[MODEL_TARGET],
    )
    print(f"\nBest model → {args.checkpoint_dir / 'best_model.pt'}")
    print(f"Last model → {args.checkpoint_dir / 'last_model.pt'}")


if __name__ == "__main__":
    main()
