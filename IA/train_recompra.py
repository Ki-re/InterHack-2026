"""Train a dedicated binary classifier for vuelve_a_comprar.

Usage:
    conda run -n interhack python IA/train_recompra.py \
        --csv IA/dataset_modelo.csv \
        --epochs 250 --batch-size 2048 --lr 5e-4 \
        --weight-decay 5e-4 --hidden-sizes "512,256,128" \
        --dropout 0.25 --checkpoint-dir IA/checkpoints_recompra \
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
    ID_OR_LEAKAGE_COLS,
    TARGET_COLS,
    build_trunk,
    describe_device,
    finalize_totals,
    get_device,
    make_dataloader,
    make_json_safe_config,
    parse_hidden_sizes,
    print_target_analysis,
    save_checkpoint,
    split_dataframe,
    build_features,
    update_totals,
)

MODEL_TARGET = "vuelve_a_comprar"
LABEL_SMOOTHING = 0.05


class RecompraModel(nn.Module):
    """Binary classifier for vuelve_a_comprar."""

    def __init__(self, input_size: int, hidden_sizes: list[int], dropout: float = 0.25) -> None:
        super().__init__()
        self.trunk, out_features = build_trunk(input_size, hidden_sizes, dropout)
        self.head = nn.Linear(out_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.trunk(x)).squeeze(1)  # raw logit


def compute_loss(logits: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    smooth_target = target * (1 - 2 * LABEL_SMOOTHING) + LABEL_SMOOTHING
    loss = nn.functional.binary_cross_entropy_with_logits(logits, smooth_target)
    return loss, {"loss": float(loss.detach().cpu())}


@torch.no_grad()
def compute_metrics(logits: torch.Tensor, target: torch.Tensor) -> dict[str, float]:
    preds = (torch.sigmoid(logits) >= 0.5).float()
    labels = target.round().clamp(0, 1)
    acc = (preds == labels).float().mean()

    tp = ((preds == 1) & (labels == 1)).float().sum()
    fp = ((preds == 1) & (labels == 0)).float().sum()
    fn = ((preds == 0) & (labels == 1)).float().sum()
    precision = tp / (tp + fp).clamp(min=1)
    recall = tp / (tp + fn).clamp(min=1)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-8)

    return {
        "acc_recompra": float(acc.cpu()),
        "precision": float(precision.cpu()),
        "recall": float(recall.cpu()),
        "f1": float(f1.cpu()),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: Any,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_samples = 0
    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device, non_blocking=True)
        y_batch = y_batch.to(device, non_blocking=True)
        logits = model(x_batch)
        _, loss_m = compute_loss(logits, y_batch)
        acc_m = compute_metrics(logits, y_batch)
        update_totals(totals, {**loss_m, **acc_m}, x_batch.size(0))
        n_samples += x_batch.size(0)
    return finalize_totals(totals, n_samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train binary classifier for vuelve_a_comprar")
    parser.add_argument("--csv", type=Path, default=Path("IA/dataset_modelo.csv"))
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--hidden-sizes", type=parse_hidden_sizes, default=parse_hidden_sizes("512,256,128"))
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("IA/checkpoints_recompra"))
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--grad-clip", type=float, default=1.0)
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

    print(f"Loaded dataset: {args.csv} rows={len(df):,}")
    print_target_analysis(df)

    train_df, val_df, test_df = split_dataframe(df, seed=args.seed)
    print(
        f"\nSplit: train={len(train_df):,} val={len(val_df):,} test={len(test_df):,}"
    )

    x_train, x_val, x_test, feature_names, feature_means, feature_stds = build_features(
        train_df, val_df, test_df
    )
    y_train = torch.tensor(train_df[MODEL_TARGET].clip(0, 1).to_numpy(dtype=np.float32))
    y_val = torch.tensor(val_df[MODEL_TARGET].clip(0, 1).to_numpy(dtype=np.float32))
    y_test = torch.tensor(test_df[MODEL_TARGET].clip(0, 1).to_numpy(dtype=np.float32))

    print(f"Input size: {x_train.shape[1]}  Hidden sizes: {args.hidden_sizes}")
    pos_rate = float(y_train.mean())
    print(f"Training positive rate: {pos_rate:.3f} ({int(y_train.sum())}/{len(y_train)})")

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

    model = RecompraModel(x_train.shape[1], args.hidden_sizes, args.dropout).to(device)
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

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_totals: dict[str, float] = {}
        n_train = 0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda", enabled=amp_enabled):
                logits = model(x_batch)
                loss, loss_m = compute_loss(logits, y_batch)
            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            update_totals(train_totals, loss_m, x_batch.size(0))
            n_train += x_batch.size(0)

        train_m = finalize_totals(train_totals, n_train)
        val_m = evaluate(model, val_loader, device)
        scheduler.step(val_m["loss"])
        current_lr = optimizer.param_groups[0]["lr"]

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
            f"val_acc={val_m['acc_recompra']:.4f} val_f1={val_m['f1']:.4f} "
            f"val_prec={val_m['precision']:.4f} val_rec={val_m['recall']:.4f} "
            f"best_epoch={best_epoch:03d}"
        )

    test_m = evaluate(model, test_loader, device)
    print("\n=== Test metrics ===")
    for key, value in test_m.items():
        print(f"  {key}: {value:.4f}")

    save_checkpoint(
        args.checkpoint_dir / "last_model.pt",
        model=model, optimizer=optimizer, scheduler=scheduler,
        epoch=args.epochs, train_metrics=train_m, val_metrics=val_m,
        test_metrics=test_m, feature_names=feature_names,
        feature_means=feature_means, feature_stds=feature_stds,
        config=config, best_val_loss=best_val_loss, target_cols=[MODEL_TARGET],
    )
    print(f"\nBest model → {args.checkpoint_dir / 'best_model.pt'}")
    print(f"Last model → {args.checkpoint_dir / 'last_model.pt'}")


if __name__ == "__main__":
    main()
