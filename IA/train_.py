from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from train_dias_common import (
    AUX_CONFIG,
    MAX_DAYS,
    add_days_features,
    build_aux_targets,
    compute_loss,
    compute_metrics,
    resolve_csv_path,
)


TARGET_COL = "dias_hasta_proxima_compra"
FILTER_COL = "vuelve_a_comprar"

TARGET_COLS = [
    "vuelve_a_comprar",
    "dias_hasta_proxima_compra",
    "target_potencial_cliente",
]

ID_COLS = [
    "Num.Fact",
    "Fecha",
    "Id. Cliente",
    "Id. Producto",
]

LEAKAGE_COLS = [
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]

INTERNAL_COLS = [
    "__dataset_source__",
    "target_log_days",
    "target_aux",
]


@dataclass(frozen=True)
class SequenceSample:
    end_idx: int
    start_idx: int
    length: int
    cut_date: pd.Timestamp
    target_log_days: float
    target_aux: int


class DaysSequenceDataset(Dataset):
    def __init__(self, features: np.ndarray, samples: list[SequenceSample]):
        self.features = features
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        x = self.features[sample.start_idx : sample.end_idx + 1]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(sample.length, dtype=torch.long),
            torch.tensor(sample.target_log_days, dtype=torch.float32),
            torch.tensor(sample.target_aux, dtype=torch.long),
        )


def collate_sequences(
    batch: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, y_days, y_aux = zip(*batch)
    padded = nn.utils.rnn.pad_sequence(xs, batch_first=True)
    return padded, torch.stack(lengths), torch.stack(y_days), torch.stack(y_aux)


class SequentialDaysModel(nn.Module):
    def __init__(
        self,
        input_size: int,
        n_aux_classes: int,
        hidden_size: int = 96,
        num_layers: int = 1,
        dropout: float = 0.25,
    ) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.shared = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 96),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(96, 48),
            nn.SiLU(),
            nn.Dropout(dropout),
        )
        self.days_head = nn.Linear(48, 1)
        self.aux_head = nn.Linear(48, n_aux_classes)
        self.positive = nn.Softplus()

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, hidden = self.gru(packed)
        features = self.shared(hidden[-1])
        pred_log_days = self.positive(self.days_head(features).squeeze(1))
        aux_logits = self.aux_head(features)
        return pred_log_days, aux_logits


def load_datasets(csv_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for csv_path in csv_paths:
        resolved = resolve_csv_path(csv_path)
        frame = pd.read_csv(resolved)
        frame["__dataset_source__"] = resolved.stem
        frames.append(frame)
    return pd.concat(frames, axis=0, ignore_index=True, sort=False)


def build_feature_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    excluded = set(TARGET_COLS) | set(ID_COLS) | set(LEAKAGE_COLS) | set(INTERNAL_COLS)
    feature_cols = [col for col in df.columns if col not in excluded]
    features = df[feature_cols].copy()
    features["dataset_source"] = df["__dataset_source__"].astype("object")
    categorical_cols = features.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    features = pd.get_dummies(features, columns=categorical_cols, dummy_na=True)
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
    return features, features.columns.tolist()


def normalize_features_by_train_rows(
    features: pd.DataFrame,
    train_row_mask: np.ndarray,
) -> tuple[np.ndarray, pd.Series, pd.Series]:
    train_features = features.loc[train_row_mask]
    means = train_features.mean()
    stds = train_features.std().replace(0, 1)
    normalized = ((features - means) / stds).astype("float32")
    return normalized.to_numpy(dtype=np.float32), means, stds


def build_sequence_samples(
    df: pd.DataFrame,
    max_seq_len: int,
    min_history: int,
) -> list[SequenceSample]:
    samples: list[SequenceSample] = []
    group_cols = ["__dataset_source__", "Id. Cliente", "Id. Producto"]

    for _, group in df.groupby(group_cols, sort=False):
        if len(group) < min_history:
            continue
        idxs = group.index.to_numpy()
        target_log_days = group["target_log_days"].to_numpy(dtype=np.float32)
        target_aux = group["target_aux"].to_numpy(dtype=np.int64)
        dates = group["Fecha"].to_numpy()

        for pos in range(min_history - 1, len(group)):
            start_pos = max(0, pos - max_seq_len + 1)
            samples.append(
                SequenceSample(
                    end_idx=int(idxs[pos]),
                    start_idx=int(idxs[start_pos]),
                    length=int(pos - start_pos + 1),
                    cut_date=pd.Timestamp(dates[pos]),
                    target_log_days=float(target_log_days[pos]),
                    target_aux=int(target_aux[pos]),
                )
            )

    return samples


def split_samples_by_date(
    samples: list[SequenceSample],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> tuple[list[SequenceSample], list[SequenceSample], list[SequenceSample]]:
    ordered = sorted(samples, key=lambda sample: sample.cut_date)
    n = len(ordered)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    return (
        ordered[:n_train],
        ordered[n_train : n_train + n_val],
        ordered[n_train + n_val :],
    )


def split_samples_random(
    samples: list[SequenceSample],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[SequenceSample], list[SequenceSample], list[SequenceSample]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(len(samples))
    rng.shuffle(indices)
    n = len(indices)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    return (
        [samples[idx] for idx in indices[:n_train]],
        [samples[idx] for idx in indices[n_train : n_train + n_val]],
        [samples[idx] for idx in indices[n_train + n_val :]],
    )


def aux_distribution(samples: list[SequenceSample], n_classes: int) -> str:
    counts = np.bincount([sample.target_aux for sample in samples], minlength=n_classes)
    ratios = counts / max(counts.sum(), 1)
    visible = [(idx, count, ratio) for idx, (count, ratio) in enumerate(zip(counts, ratios)) if count > 0]
    return ", ".join(f"{idx}={count:,} ({ratio:.1%})" for idx, count, ratio in visible)


def make_run_config(args: argparse.Namespace, aux_cfg: dict[str, Any], n_aux_classes: int) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            config[key] = str(value)
        elif isinstance(value, list):
            config[key] = [str(item) if isinstance(item, Path) else item for item in value]
        else:
            config[key] = value
    config.update(
        {
            "target_col": TARGET_COL,
            "max_days": MAX_DAYS,
            "aux_name": aux_cfg["name"],
            "aux_class_names": aux_cfg["class_names"],
            "n_aux_classes": n_aux_classes,
        }
    )
    return config


def save_sequential_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.ReduceLROnPlateau,
    epoch: int,
    train_metrics: dict[str, float],
    val_metrics: dict[str, float],
    feature_names: list[str],
    feature_means: pd.Series,
    feature_stds: pd.Series,
    config: dict[str, Any],
    best_val_loss: float,
    test_metrics: dict[str, float] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "best_val_loss": best_val_loss,
            "input_size": len(feature_names),
            "feature_names": feature_names,
            "feature_means": feature_means.to_dict(),
            "feature_stds": feature_stds.to_dict(),
            "target_cols": [TARGET_COL, AUX_CONFIG[config["aux_task"]]["target_col"]],
            "config": config,
        },
        path,
    )


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    aux_loss_weight: float,
    n_aux_classes: int,
    days_tolerance_abs: float,
    days_tolerance_abs2: float,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_samples = 0
    for x, lengths, y_days, y_aux in loader:
        x = x.to(device)
        lengths = lengths.to(device)
        y_days = y_days.to(device)
        y_aux = y_aux.to(device)
        pred = model(x, lengths)
        _, loss_m = compute_loss(pred, y_days, y_aux, aux_loss_weight)
        metric_m = compute_metrics(pred, y_days, y_aux, n_aux_classes, days_tolerance_abs, days_tolerance_abs2)
        batch_size = x.size(0)
        for key, value in {**loss_m, **metric_m}.items():
            totals[key] = totals.get(key, 0.0) + value * batch_size
        n_samples += batch_size
    return {key: value / max(n_samples, 1) for key, value in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train sequential model for days until next purchase")
    parser.add_argument("--csv", type=Path, nargs="+", default=[Path("dataset_v2.csv")])
    parser.add_argument("--output", type=Path, default=Path("purchase_sequential_days_model_month.pt"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("IA/checkpoints_secuencial_dias"))
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--split", choices=["random", "temporal"], default="random")
    parser.add_argument("--aux-task", choices=["months", "ranges", "biweekly"], default="months")
    parser.add_argument("--max-seq-len", type=int, default=12)
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-size", type=int, default=96)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--aux-loss-weight", type=float, default=0.35)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--metric-days-tolerance", type=float, default=3.0)
    parser.add_argument("--metric-days-tolerance2", type=float, default=20.0)
    parser.add_argument("--early-stopping-patience", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = load_datasets(args.csv)
    required = ["Fecha", "Id. Cliente", "Id. Producto", TARGET_COL, FILTER_COL]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=required).copy()
    n_before = len(df)
    df = df[df[FILTER_COL] == 1].copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"]).copy()
    df[TARGET_COL] = df[TARGET_COL].clip(lower=0, upper=MAX_DAYS)
    df = add_days_features(df)
    df["target_log_days"] = np.log1p(df[TARGET_COL].to_numpy(dtype=np.float32))
    df["target_aux"] = build_aux_targets(df[TARGET_COL].to_numpy(dtype=np.float32), args.aux_task).numpy()
    df = df.sort_values(
        ["__dataset_source__", "Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"],
        kind="mergesort",
    ).reset_index(drop=True)

    aux_cfg = AUX_CONFIG[args.aux_task]
    n_aux_classes = len(aux_cfg["class_names"])
    print(
        "Loaded datasets: "
        f"{', '.join(str(path) for path in args.csv)}; "
        f"rows={n_before:,}; buyers={len(df):,}; target capped to {MAX_DAYS:.0f} days"
    )
    print(f"Aux task: {aux_cfg['name']} ({n_aux_classes} classes)")

    raw_samples = build_sequence_samples(df, max_seq_len=args.max_seq_len, min_history=args.min_history)
    if not raw_samples:
        raise ValueError("No sequence samples were created. Lower --min-history or check client-product history.")

    if args.split == "random":
        train_samples, val_samples, test_samples = split_samples_random(raw_samples, seed=args.seed)
    else:
        train_samples, val_samples, test_samples = split_samples_by_date(raw_samples)

    train_end_indices = {sample.end_idx for sample in train_samples}
    train_row_mask = df.index.isin(train_end_indices)
    feature_frame, feature_names = build_feature_frame(df)
    features, feature_means, feature_stds = normalize_features_by_train_rows(feature_frame, train_row_mask)

    print(
        "Samples: "
        f"train={len(train_samples):,}, val={len(val_samples):,}, test={len(test_samples):,}; "
        f"features={features.shape[1]:,}; max_seq_len={args.max_seq_len}"
    )
    print(f"Train aux distribution: {aux_distribution(train_samples, n_aux_classes)}")
    print(f"Val aux distribution:   {aux_distribution(val_samples, n_aux_classes)}")
    print(f"Test aux distribution:  {aux_distribution(test_samples, n_aux_classes)}")

    train_loader = DataLoader(
        DaysSequenceDataset(features, train_samples),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_sequences,
    )
    val_loader = DataLoader(
        DaysSequenceDataset(features, val_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )
    test_loader = DataLoader(
        DaysSequenceDataset(features, test_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SequentialDaysModel(
        input_size=features.shape[1],
        n_aux_classes=n_aux_classes,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)
    config = make_run_config(args, aux_cfg, n_aux_classes)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (args.checkpoint_dir / "run_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Checkpoint dir: {args.checkpoint_dir}")

    best_state = None
    best_epoch = 0
    best_val_loss = float("inf")
    last_epoch = 0
    last_train_metrics: dict[str, float] = {}
    last_val_metrics: dict[str, float] = {}

    for epoch in range(1, args.epochs + 1):
        model.train()
        for x, lengths, y_days, y_aux in train_loader:
            x = x.to(device)
            lengths = lengths.to(device)
            y_days = y_days.to(device)
            y_aux = y_aux.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss, _ = compute_loss(model(x, lengths), y_days, y_aux, args.aux_loss_weight)
            loss.backward()
            if args.grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
            optimizer.step()

        train_metrics = evaluate(
            model, train_loader, device, args.aux_loss_weight, n_aux_classes,
            args.metric_days_tolerance, args.metric_days_tolerance2,
        )
        val_metrics = evaluate(
            model, val_loader, device, args.aux_loss_weight, n_aux_classes,
            args.metric_days_tolerance, args.metric_days_tolerance2,
        )
        scheduler.step(val_metrics["loss"])
        last_epoch = epoch
        last_train_metrics = train_metrics
        last_val_metrics = val_metrics

        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            save_sequential_checkpoint(
                args.checkpoint_dir / "best_model.pt",
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                epoch=epoch,
                train_metrics=train_metrics,
                val_metrics=val_metrics,
                feature_names=feature_names,
                feature_means=feature_means,
                feature_stds=feature_stds,
                config=config,
                best_val_loss=best_val_loss,
            )

        if args.checkpoint_every > 0 and epoch % args.checkpoint_every == 0:
            save_sequential_checkpoint(
                args.checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.pt",
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                epoch=epoch,
                train_metrics=train_metrics,
                val_metrics=val_metrics,
                feature_names=feature_names,
                feature_means=feature_means,
                feature_stds=feature_stds,
                config=config,
                best_val_loss=best_val_loss,
            )

        print(
            f"Epoch {epoch:03d} "
            f"train_loss={train_metrics['loss']:.4f} "
            f"train_mae={train_metrics['mae_days']:.1f}d "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_mae={val_metrics['mae_days']:.1f}d "
            f"val_acc_pm3={val_metrics['acc_dias_pm3']:.4f} "
            f"val_acc_pm20={val_metrics['acc_dias_pm20']:.4f} "
            f"val_acc_aux={val_metrics['acc_aux']:.4f} "
            f"val_f1_aux={val_metrics['f1_aux_macro']:.4f} "
            f"lr={optimizer.param_groups[0]['lr']:.6f}"
        )

        if epoch - best_epoch >= args.early_stopping_patience:
            print(f"Early stopping at epoch {epoch}; best epoch was {best_epoch}.")
            break

    save_sequential_checkpoint(
        args.checkpoint_dir / "last_model.pt",
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        epoch=last_epoch,
        train_metrics=last_train_metrics,
        val_metrics=last_val_metrics,
        feature_names=feature_names,
        feature_means=feature_means,
        feature_stds=feature_stds,
        config=config,
        best_val_loss=best_val_loss,
    )

    if best_state is not None:
        model.load_state_dict(best_state)

    test_metrics = evaluate(
        model, test_loader, device, args.aux_loss_weight, n_aux_classes,
        args.metric_days_tolerance, args.metric_days_tolerance2,
    )
    print("\n=== Test metrics ===")
    for key, value in test_metrics.items():
        print(f"{key}: {value:.4f}")

    best_checkpoint_path = args.checkpoint_dir / "best_model.pt"
    if best_checkpoint_path.exists():
        best_checkpoint = torch.load(best_checkpoint_path, map_location="cpu")
        best_checkpoint["test_metrics"] = test_metrics
        torch.save(best_checkpoint, best_checkpoint_path)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": features.shape[1],
            "feature_names": feature_names,
            "feature_means": feature_means.to_dict(),
            "feature_stds": feature_stds.to_dict(),
            "target_col": TARGET_COL,
            "max_days": MAX_DAYS,
            "aux_task": args.aux_task,
            "aux_name": aux_cfg["name"],
            "aux_class_names": aux_cfg["class_names"],
            "csv_paths": [str(path) for path in args.csv],
            "max_seq_len": args.max_seq_len,
            "min_history": args.min_history,
            "hidden_size": args.hidden_size,
            "num_layers": args.num_layers,
            "dropout": args.dropout,
            "aux_loss_weight": args.aux_loss_weight,
            "best_epoch": best_epoch,
            "test_metrics": test_metrics,
        },
        args.output,
    )
    print(f"\nSaved model to {args.output}")
    print(f"Best model -> {args.checkpoint_dir / 'best_model.pt'}")
    print(f"Last model -> {args.checkpoint_dir / 'last_model.pt'}")


if __name__ == "__main__":
    main()
