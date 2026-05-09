from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


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


@dataclass(frozen=True)
class SequenceSample:
    end_idx: int
    start_idx: int
    length: int
    cut_date: pd.Timestamp
    target_recompra: float
    target_days_norm: float
    target_value_norm: float
    target_days_real: float
    target_value_real: float


class ClientProductSequenceDataset(Dataset):
    def __init__(self, features: np.ndarray, samples: list[SequenceSample]):
        self.features = features
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        x = self.features[sample.start_idx : sample.end_idx + 1]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(sample.length, dtype=torch.long),
            torch.tensor(sample.target_recompra, dtype=torch.float32),
            torch.tensor(sample.target_days_norm, dtype=torch.float32),
            torch.tensor(sample.target_value_norm, dtype=torch.float32),
        )


def collate_sequences(
    batch: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, y_recompra, y_days, y_value = zip(*batch)
    padded = nn.utils.rnn.pad_sequence(xs, batch_first=True)
    return (
        padded,
        torch.stack(lengths),
        torch.stack(y_recompra),
        torch.stack(y_days),
        torch.stack(y_value),
    )


class SequentialPurchaseModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 1, dropout: float = 0.15):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.recompra_head = nn.Linear(64, 1)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, hidden = self.gru(packed)
        encoded = hidden[-1]
        shared = self.head(encoded)
        return torch.sigmoid(self.recompra_head(shared).squeeze(1))


def build_feature_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    excluded = set(TARGET_COLS) | set(ID_COLS) | set(LEAKAGE_COLS)
    feature_cols = [col for col in df.columns if col not in excluded]
    features = df[feature_cols].copy()
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
    horizon_days: int,
    min_history: int,
) -> list[SequenceSample]:
    samples: list[SequenceSample] = []
    horizon = pd.Timedelta(days=horizon_days)

    for _, group in df.groupby(["Id. Cliente", "Id. Producto"], sort=False):
        if len(group) <= min_history:
            continue
        idxs = group.index.to_numpy()
        dates = group["Fecha"].to_numpy()
        values = group["Valores_H"].fillna(0).clip(lower=0).to_numpy(dtype=np.float32)

        for pos in range(min_history - 1, len(group)):
            cut_date = pd.Timestamp(dates[pos])
            future_start = pos + 1
            if future_start >= len(group):
                future_mask = np.zeros(0, dtype=bool)
            else:
                future_dates = pd.to_datetime(dates[future_start:])
                future_mask = future_dates <= cut_date + horizon

            if future_mask.any():
                first_future_pos = future_start + int(np.flatnonzero(future_mask)[0])
                first_future_date = pd.Timestamp(dates[first_future_pos])
                days_real = float((first_future_date - cut_date).days)
                value_real = float(values[future_start:][future_mask].sum())
                recompra = 1.0
            else:
                days_real = float(horizon_days)
                value_real = 0.0
                recompra = 0.0

            start_pos = max(0, pos - max_seq_len + 1)
            start_idx = int(idxs[start_pos])
            end_idx = int(idxs[pos])
            length = int(pos - start_pos + 1)
            samples.append(
                SequenceSample(
                    end_idx=end_idx,
                    start_idx=start_idx,
                    length=length,
                    cut_date=cut_date,
                    target_recompra=recompra,
                    target_days_norm=0.0,
                    target_value_norm=0.0,
                    target_days_real=days_real,
                    target_value_real=value_real,
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


def split_samples_stratified(
    samples: list[SequenceSample],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[SequenceSample], list[SequenceSample], list[SequenceSample]]:
    rng = np.random.default_rng(seed)
    train_samples: list[SequenceSample] = []
    val_samples: list[SequenceSample] = []
    test_samples: list[SequenceSample] = []

    for target_value in (0.0, 1.0):
        class_samples = [sample for sample in samples if sample.target_recompra == target_value]
        class_indices = np.arange(len(class_samples))
        rng.shuffle(class_indices)

        n = len(class_indices)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train_samples.extend(class_samples[idx] for idx in class_indices[:n_train])
        val_samples.extend(class_samples[idx] for idx in class_indices[n_train : n_train + n_val])
        test_samples.extend(class_samples[idx] for idx in class_indices[n_train + n_val :])

    rng.shuffle(train_samples)
    rng.shuffle(val_samples)
    rng.shuffle(test_samples)
    return train_samples, val_samples, test_samples


def add_normalized_targets(
    train_samples: list[SequenceSample],
    val_samples: list[SequenceSample],
    test_samples: list[SequenceSample],
) -> tuple[list[SequenceSample], list[SequenceSample], list[SequenceSample], dict[str, float]]:
    train_days_log = np.log1p([sample.target_days_real for sample in train_samples])
    train_value_log = np.log1p([sample.target_value_real for sample in train_samples])
    days_mean = float(train_days_log.mean())
    days_std = float(train_days_log.std() or 1.0)
    value_mean = float(train_value_log.mean())
    value_std = float(train_value_log.std() or 1.0)

    def normalize(samples: list[SequenceSample]) -> list[SequenceSample]:
        normalized = []
        for sample in samples:
            normalized.append(
                SequenceSample(
                    end_idx=sample.end_idx,
                    start_idx=sample.start_idx,
                    length=sample.length,
                    cut_date=sample.cut_date,
                    target_recompra=sample.target_recompra,
                    target_days_norm=(float(np.log1p(sample.target_days_real)) - days_mean) / days_std,
                    target_value_norm=(float(np.log1p(sample.target_value_real)) - value_mean) / value_std,
                    target_days_real=sample.target_days_real,
                    target_value_real=sample.target_value_real,
                )
            )
        return normalized

    metadata = {
        "days_mean": days_mean,
        "days_std": days_std,
        "value_mean": value_mean,
        "value_std": value_std,
    }
    return normalize(train_samples), normalize(val_samples), normalize(test_samples), metadata


def compute_loss(
    pred: torch.Tensor,
    y_recompra: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, float]]:
    loss = nn.functional.binary_cross_entropy(pred, y_recompra)
    return loss, {"loss": float(loss.detach().cpu()), "bce_recompra": float(loss.detach().cpu())}


def binary_f1(pred_label: torch.Tensor, target: torch.Tensor) -> tuple[float, float, float]:
    pred_bool = pred_label.bool()
    target_bool = target.bool()
    tp = (pred_bool & target_bool).sum().float()
    fp = (pred_bool & ~target_bool).sum().float()
    fn = (~pred_bool & target_bool).sum().float()
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    return (
        float(precision.detach().cpu()),
        float(recall.detach().cpu()),
        float(f1.detach().cpu()),
    )


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_batches = 0
    for x, lengths, y_recompra, y_days, y_value in loader:
        x = x.to(device)
        lengths = lengths.to(device)
        y_recompra = y_recompra.to(device)
        y_days = y_days.to(device)
        y_value = y_value.to(device)
        pred = model(x, lengths)
        _, metrics = compute_loss(pred, y_recompra)

        recompra_label = (pred >= 0.5).float()
        precision, recall, f1 = binary_f1(recompra_label, y_recompra)
        acc = (recompra_label == y_recompra).float().mean()

        metrics.update(
            {
                "acc_recompra": float(acc.detach().cpu()),
                "precision_recompra": precision,
                "recall_recompra": recall,
                "f1_recompra": f1,
            }
        )
        for key, value in metrics.items():
            totals[key] = totals.get(key, 0.0) + value
        n_batches += 1
    return {key: value / max(n_batches, 1) for key, value in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("dataset_modelo_previo.csv"))
    parser.add_argument("--output", type=Path, default=Path("purchase_sequential_recompra_model.pt"))
    parser.add_argument("--split", choices=["stratified", "temporal"], default="stratified")
    parser.add_argument("--horizon-days", type=int, default=365)
    parser.add_argument("--max-seq-len", type=int, default=12)
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.15)
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = pd.read_csv(args.csv)
    required = ["Fecha", "Id. Cliente", "Id. Producto", "Valores_H"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=required).copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df = df.sort_values(["Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"], kind="mergesort").reset_index(drop=True)
    print(f"Loaded rows={len(df):,} columns={len(df.columns):,}")

    raw_samples = build_sequence_samples(
        df,
        max_seq_len=args.max_seq_len,
        horizon_days=args.horizon_days,
        min_history=args.min_history,
    )
    if not raw_samples:
        raise ValueError("No sequence samples were created. Lower --min-history or check client-product history.")

    if args.split == "stratified":
        train_samples, val_samples, test_samples = split_samples_stratified(raw_samples, seed=args.seed)
    else:
        train_samples, val_samples, test_samples = split_samples_by_date(raw_samples)
    train_samples, val_samples, test_samples, _ = add_normalized_targets(train_samples, val_samples, test_samples)

    train_end_indices = {sample.end_idx for sample in train_samples}
    train_row_mask = df.index.isin(train_end_indices)
    feature_frame, feature_names = build_feature_frame(df)
    features, feature_means, feature_stds = normalize_features_by_train_rows(feature_frame, train_row_mask)

    print(
        "Samples: "
        f"train={len(train_samples):,}, val={len(val_samples):,}, test={len(test_samples):,}; "
        f"features={features.shape[1]:,}; max_seq_len={args.max_seq_len}"
    )
    print(
        "Positive recompra ratio: "
        f"train={np.mean([s.target_recompra for s in train_samples]):.2%}, "
        f"val={np.mean([s.target_recompra for s in val_samples]):.2%}, "
        f"test={np.mean([s.target_recompra for s in test_samples]):.2%}"
    )

    train_loader = DataLoader(
        ClientProductSequenceDataset(features, train_samples),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_sequences,
    )
    val_loader = DataLoader(
        ClientProductSequenceDataset(features, val_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )
    test_loader = DataLoader(
        ClientProductSequenceDataset(features, test_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SequentialPurchaseModel(
        input_size=features.shape[1],
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)

    best_state = None
    best_epoch = 0
    best_val_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        model.train()
        for x, lengths, y_recompra, y_days, y_value in train_loader:
            x = x.to(device)
            lengths = lengths.to(device)
            y_recompra = y_recompra.to(device)
            y_days = y_days.to(device)
            y_value = y_value.to(device)
            optimizer.zero_grad()
            loss, _ = compute_loss(model(x, lengths), y_recompra)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

        train_metrics = evaluate(model, train_loader, device)
        val_metrics = evaluate(model, val_loader, device)
        scheduler.step(val_metrics["loss"])

        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

        print(
            f"Epoch {epoch:03d} "
            f"train_loss={train_metrics['loss']:.4f} "
            f"train_acc={train_metrics['acc_recompra']:.4f} "
            f"train_f1={train_metrics['f1_recompra']:.4f} "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_acc={val_metrics['acc_recompra']:.4f} "
            f"val_f1={val_metrics['f1_recompra']:.4f} "
            f"lr={optimizer.param_groups[0]['lr']:.6f}"
        )

        if epoch - best_epoch >= args.early_stopping_patience:
            print(f"Early stopping at epoch {epoch}; best epoch was {best_epoch}.")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    test_metrics = evaluate(model, test_loader, device)
    print("\n=== Test metrics ===")
    for key, value in test_metrics.items():
        print(f"{key}: {value:.4f}")

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": features.shape[1],
            "feature_names": feature_names,
            "feature_means": feature_means,
            "feature_stds": feature_stds,
            "target_col": "vuelve_a_comprar",
            "horizon_days": args.horizon_days,
            "max_seq_len": args.max_seq_len,
            "min_history": args.min_history,
            "hidden_size": args.hidden_size,
            "num_layers": args.num_layers,
            "dropout": args.dropout,
            "best_epoch": best_epoch,
        },
        args.output,
    )
    print(f"\nSaved model to {args.output}")


if __name__ == "__main__":
    main()
