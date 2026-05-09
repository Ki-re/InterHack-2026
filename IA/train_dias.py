"""Train a dedicated regression model for dias_hasta_proxima_compra.

Key differences from the combined model:
  - Trained on BUYERS ONLY (vuelve_a_comprar == 1)
  - Target is log1p-transformed to tame the 0–1780 day range
  - SmoothL1 (Huber) loss in log-space
  - Reports ±3, ±20 (absolute) and ±10% (relative) accuracy in original day space

Usage:
    conda run -n interhack python IA/train_dias.py \
        --csv IA/dataset_modelo.csv \
        --epochs 250 --batch-size 2048 --lr 5e-4 \
        --weight-decay 5e-4 --hidden-sizes "512,256,128,64" \
        --dropout 0.25 --checkpoint-dir IA/checkpoints_dias \
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

MODEL_TARGET = "dias_hasta_proxima_compra"
FILTER_COL = "vuelve_a_comprar"


class DiasModel(nn.Module):
    """Regression model for days-until-next-purchase (buyers only).

    Predicts in log1p space. Softplus ensures the output is positive,
    which is correct since log1p(days) >= 0 for days >= 0.
    """

    def __init__(self, input_size: int, hidden_sizes: list[int], dropout: float = 0.25) -> None:
        super().__init__()
        self.trunk, out_features = build_trunk(input_size, hidden_sizes, dropout)
        self.head = nn.Linear(out_features, 1)
        self.positive = nn.Softplus()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.positive(self.head(self.trunk(x)).squeeze(1))


def compute_loss(pred_log: torch.Tensor, target_log: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    """Huber loss in log1p space."""
    loss = nn.functional.smooth_l1_loss(pred_log, target_log)
    return loss, {"loss": float(loss.detach().cpu()), "huber_log_dias": float(loss.detach().cpu())}


@torch.no_grad()
def compute_metrics(
    pred_log: torch.Tensor,
    target_log: torch.Tensor,
    days_tolerance_abs: float = 3.0,
    days_tolerance_abs2: float = 20.0,
) -> dict[str, float]:
    pred_days = torch.expm1(pred_log).clamp(min=0)
    target_days = torch.expm1(target_log).clamp(min=0)

    diff = torch.abs(pred_days - target_days)
    acc_pm3 = (diff <= days_tolerance_abs).float().mean()
    acc_pm20 = (diff <= days_tolerance_abs2).float().mean()

    # Avoid division by zero for target_days == 0
    pct_err = diff / target_days.clamp(min=1)
    acc_pct10 = (pct_err <= 0.10).float().mean()

    mae = diff.mean()

    return {
        "acc_dias_pm3": float(acc_pm3.cpu()),
        "acc_dias_pm20": float(acc_pm20.cpu()),
        "acc_dias_pct10": float(acc_pct10.cpu()),
        "mae_days": float(mae.cpu()),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: Any,
    device: torch.device,
    days_tolerance_abs: float,
    days_tolerance_abs2: float,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_samples = 0
    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device, non_blocking=True)
        y_batch = y_batch.to(device, non_blocking=True)
        pred_log = model(x_batch)
        _, loss_m = compute_loss(pred_log, y_batch)
        acc_m = compute_metrics(pred_log, y_batch, days_tolerance_abs, days_tolerance_abs2)
        update_totals(totals, {**loss_m, **acc_m}, x_batch.size(0))
        n_samples += x_batch.size(0)
    return finalize_totals(totals, n_samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train regression model for dias (buyers only)")
    parser.add_argument("--csv", type=Path, default=Path("IA/dataset_modelo.csv"))
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--hidden-sizes", type=parse_hidden_sizes, default=parse_hidden_sizes("512,256,128,64"))
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("IA/checkpoints_dias"))
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--metric-days-tolerance", type=float, default=3.0,
                        help="Absolute day tolerance for acc_pm3 metric (default: 3)")
    parser.add_argument("--metric-days-tolerance2", type=float, default=20.0,
                        help="Second absolute day tolerance for acc_pm20 metric (default: 20)")
    parser.add_argument("--sample-rows", type=int, default=0)
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=[MODEL_TARGET, FILTER_COL]).reset_index(drop=True)

    # Filter to buyers only
    n_before = len(df)
    df = df[df[FILTER_COL] == 1].reset_index(drop=True)
    print(f"Loaded {args.csv}: {n_before:,} rows → {len(df):,} buyers after filtering vuelve_a_comprar==1")

    if args.sample_rows > 0 and args.sample_rows < len(df):
        df = df.sample(n=args.sample_rows, random_state=args.seed).reset_index(drop=True)
        print(f"Using sampled dataset: rows={len(df):,}")

    print(f"\ndias_hasta_proxima_compra stats (buyers only):")
    print(df[MODEL_TARGET].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))

    train_df, val_df, test_df = split_dataframe(df, seed=args.seed)
    print(f"\nSplit: train={len(train_df):,} val={len(val_df):,} test={len(test_df):,}")

    x_train, x_val, x_test, feature_names, feature_means, feature_stds = build_features(
        train_df, val_df, test_df
    )

    # Target: log1p-transformed days
    y_train = torch.tensor(np.log1p(train_df[MODEL_TARGET].clip(lower=0).to_numpy(dtype=np.float32)))
    y_val = torch.tensor(np.log1p(val_df[MODEL_TARGET].clip(lower=0).to_numpy(dtype=np.float32)))
    y_test = torch.tensor(np.log1p(test_df[MODEL_TARGET].clip(lower=0).to_numpy(dtype=np.float32)))

    print(f"\nInput size: {x_train.shape[1]}  Hidden sizes: {args.hidden_sizes}")
    print(f"Log1p target — train mean: {float(y_train.mean()):.3f}  std: {float(y_train.std()):.3f}")

    device = get_device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    pin_memory = device.type == "cuda"

    train_loader = make_dataloader(x_train, y_train, args.batch_size, shuffle=True,
                                   num_workers=args.num_workers, pin_memory=pin_memory)
    val_loader = make_dataloader(x_val, y_val, args.batch_size,
                                 num_workers=args.num_workers, pin_memory=pin_memory)
    test_loader = make_dataloader(x_test, y_test, args.batch_size,
                                  num_workers=args.num_workers, pin_memory=pin_memory)

    model = DiasModel(x_train.shape[1], args.hidden_sizes, args.dropout).to(device)
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
                pred_log = model(x_batch)
                loss, loss_m = compute_loss(pred_log, y_batch)
            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            update_totals(train_totals, loss_m, x_batch.size(0))
            n_train += x_batch.size(0)

        train_m = finalize_totals(train_totals, n_train)
        val_m = evaluate(model, val_loader, device, args.metric_days_tolerance, args.metric_days_tolerance2)
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

        print(
            f"Epoch {epoch:03d} lr={current_lr:.2e} "
            f"train_loss={train_m['loss']:.4f} val_loss={val_m['loss']:.4f} "
            f"val_mae={val_m['mae_days']:.1f}d "
            f"val_acc_pm3={val_m['acc_dias_pm3']:.4f} "
            f"val_acc_pm20={val_m['acc_dias_pm20']:.4f} "
            f"val_acc_pct10={val_m['acc_dias_pct10']:.4f} "
            f"best_epoch={best_epoch:03d}"
        )

    test_m = evaluate(model, test_loader, device, args.metric_days_tolerance, args.metric_days_tolerance2)
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
