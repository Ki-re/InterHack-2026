from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


TARGET_COL = "target_potencial_cliente"
POTENCIAL_CLASS_NAMES = [
    "muy_negativo",
    "negativo",
    "estable",
    "positivo",
    "muy_positivo",
]
POTENCIAL_BINS = [-1.01, -0.5, -0.1, 0.1, 0.5, 1.01]

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
    "target_class",
]


@dataclass(frozen=True)
class SequenceSample:
    end_idx: int
    start_idx: int
    length: int
    cut_date: pd.Timestamp
    target_class: int


class PotentialSequenceDataset(Dataset):
    def __init__(self, features: np.ndarray, samples: list[SequenceSample]):
        self.features = features
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        x = self.features[sample.start_idx : sample.end_idx + 1]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(sample.length, dtype=torch.long),
            torch.tensor(sample.target_class, dtype=torch.long),
        )


def collate_sequences(
    batch: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, y = zip(*batch)
    padded = nn.utils.rnn.pad_sequence(xs, batch_first=True)
    return padded, torch.stack(lengths), torch.stack(y)


class SequentialPotentialModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 1, dropout: float = 0.25):
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
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, len(POTENCIAL_CLASS_NAMES)),
        )

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, hidden = self.gru(packed)
        return self.head(hidden[-1])


def potential_to_class(series: pd.Series) -> pd.Series:
    return pd.cut(
        series.clip(-1, 1),
        bins=POTENCIAL_BINS,
        labels=False,
        include_lowest=True,
    ).astype("int64")


def load_datasets(csv_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for csv_path in csv_paths:
        frame = pd.read_csv(csv_path)
        frame["__dataset_source__"] = csv_path.stem
        frames.append(frame)
    return pd.concat(frames, axis=0, ignore_index=True, sort=False)


def build_feature_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    excluded = set(TARGET_COLS) | set(ID_COLS) | set(LEAKAGE_COLS)
    feature_cols = [col for col in df.columns if col not in excluded and col not in INTERNAL_COLS]
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
        target_classes = group["target_class"].to_numpy(dtype=np.int64)
        dates = group["Fecha"].to_numpy()

        for pos in range(min_history - 1, len(group)):
            start_pos = max(0, pos - max_seq_len + 1)
            samples.append(
                SequenceSample(
                    end_idx=int(idxs[pos]),
                    start_idx=int(idxs[start_pos]),
                    length=int(pos - start_pos + 1),
                    cut_date=pd.Timestamp(dates[pos]),
                    target_class=int(target_classes[pos]),
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

    for class_idx in range(len(POTENCIAL_CLASS_NAMES)):
        class_samples = [sample for sample in samples if sample.target_class == class_idx]
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


def class_distribution(samples: list[SequenceSample]) -> str:
    counts = np.bincount(
        [sample.target_class for sample in samples],
        minlength=len(POTENCIAL_CLASS_NAMES),
    )
    ratios = counts / max(counts.sum(), 1)
    return ", ".join(
        f"{name}={count:,} ({ratio:.2%})"
        for name, count, ratio in zip(POTENCIAL_CLASS_NAMES, counts, ratios)
    )


def macro_precision_recall_f1(
    pred_label: torch.Tensor,
    target_label: torch.Tensor,
    num_classes: int,
) -> tuple[float, float, float]:
    precisions = []
    recalls = []
    f1s = []
    for class_idx in range(num_classes):
        pred_bool = pred_label == class_idx
        target_bool = target_label == class_idx
        tp = (pred_bool & target_bool).sum().float()
        fp = (pred_bool & ~target_bool).sum().float()
        fn = (~pred_bool & target_bool).sum().float()
        precision = tp / (tp + fp + 1e-9)
        recall = tp / (tp + fn + 1e-9)
        f1 = 2 * precision * recall / (precision + recall + 1e-9)
        precisions.append(float(precision.detach().cpu()))
        recalls.append(float(recall.detach().cpu()))
        f1s.append(float(f1.detach().cpu()))
    return float(np.mean(precisions)), float(np.mean(recalls)), float(np.mean(f1s))


def compute_loss(logits: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    loss = nn.functional.cross_entropy(logits, target)
    return loss, {"loss": float(loss.detach().cpu()), "ce_potencial": float(loss.detach().cpu())}


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_batches = 0
    for x, lengths, target in loader:
        x = x.to(device)
        lengths = lengths.to(device)
        target = target.to(device)
        logits = model(x, lengths)
        _, metrics = compute_loss(logits, target)
        pred_label = logits.argmax(dim=1)
        acc = (pred_label == target).float().mean()
        precision, recall, f1 = macro_precision_recall_f1(
            pred_label,
            target,
            len(POTENCIAL_CLASS_NAMES),
        )
        metrics.update(
            {
                "acc_potencial": float(acc.detach().cpu()),
                "precision_potencial_macro": precision,
                "recall_potencial_macro": recall,
                "f1_potencial_macro": f1,
            }
        )
        for key, value in metrics.items():
            totals[key] = totals.get(key, 0.0) + value
        n_batches += 1
    return {key: value / max(n_batches, 1) for key, value in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train sequential potential model")
    parser.add_argument("--csv", type=Path, nargs="+", default=[Path("dataset_v2.csv")])
    parser.add_argument("--output", type=Path, default=Path("models/potential_model.pt"))
    parser.add_argument("--split", choices=["stratified", "temporal"], default="stratified")
    parser.add_argument("--max-seq-len", type=int, default=12)
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--early-stopping-patience", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = load_datasets(args.csv)
    required = ["Fecha", "Id. Cliente", "Id. Producto", TARGET_COL]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=required).copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["target_class"] = potential_to_class(df[TARGET_COL])
    df = df.sort_values(
        ["__dataset_source__", "Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"],
        kind="mergesort",
    ).reset_index(drop=True)
    print(
        "Loaded datasets: "
        f"{', '.join(str(path) for path in args.csv)}; rows={len(df):,}; columns={len(df.columns):,}"
    )

    raw_samples = build_sequence_samples(
        df,
        max_seq_len=args.max_seq_len,
        min_history=args.min_history,
    )
    if not raw_samples:
        raise ValueError("No sequence samples were created. Lower --min-history or check client-product history.")

    if args.split == "stratified":
        train_samples, val_samples, test_samples = split_samples_stratified(raw_samples, seed=args.seed)
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
    print(f"Train potential distribution: {class_distribution(train_samples)}")
    print(f"Val potential distribution:   {class_distribution(val_samples)}")
    print(f"Test potential distribution:  {class_distribution(test_samples)}")

    train_loader = DataLoader(
        PotentialSequenceDataset(features, train_samples),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_sequences,
    )
    val_loader = DataLoader(
        PotentialSequenceDataset(features, val_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )
    test_loader = DataLoader(
        PotentialSequenceDataset(features, test_samples),
        batch_size=args.batch_size,
        collate_fn=collate_sequences,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SequentialPotentialModel(
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
        for x, lengths, target in train_loader:
            x = x.to(device)
            lengths = lengths.to(device)
            target = target.to(device)
            optimizer.zero_grad()
            loss, _ = compute_loss(model(x, lengths), target)
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
            f"train_acc={train_metrics['acc_potencial']:.4f} "
            f"train_f1_macro={train_metrics['f1_potencial_macro']:.4f} "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_acc={val_metrics['acc_potencial']:.4f} "
            f"val_f1_macro={val_metrics['f1_potencial_macro']:.4f} "
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": features.shape[1],
            "feature_names": feature_names,
            "feature_means": feature_means,
            "feature_stds": feature_stds,
            "target_col": TARGET_COL,
            "potencial_class_names": POTENCIAL_CLASS_NAMES,
            "potencial_bins": POTENCIAL_BINS,
            "csv_paths": [str(path) for path in args.csv],
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
