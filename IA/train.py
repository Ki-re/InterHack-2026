from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


TARGET_COLS = [
    "vuelve_a_comprar",
    "dias_hasta_proxima_compra",
    "target_potencial_cliente",
]

ID_OR_LEAKAGE_COLS = [
    "Num.Fact",
    "Fecha",
    "Id. Cliente",
    "Id. Producto",
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]


class PurchaseModel(nn.Module):
    """input -> 32 hidden units -> 3 constrained outputs."""

    def __init__(self, input_size: int, hidden_size: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 3),
        )
        self.positive = nn.Softplus()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raw = self.net(x)
        return torch.stack(
            [
                torch.sigmoid(raw[:, 0]),  # vuelve_a_comprar: 0..1
                self.positive(raw[:, 1]),  # dias_hasta_proxima_compra: 0..inf
                torch.tanh(raw[:, 2]),  # target_potencial_cliente: -1..1
            ],
            dim=1,
        )


def print_target_analysis(df: pd.DataFrame) -> None:
    print("\n=== Target analysis ===")
    for col in TARGET_COLS:
        print(f"\n{col}")
        print(df[col].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))

    print("\nvuelve_a_comprar value counts")
    print(df["vuelve_a_comprar"].value_counts(dropna=False).sort_index())

    print("\ntarget_potencial_cliente buckets")
    buckets = pd.cut(
        df["target_potencial_cliente"],
        bins=[-1.01, -0.5, -0.05, 0.05, 0.5, 1.01],
        labels=["muy_negativo", "negativo", "estable", "positivo", "muy_positivo"],
    )
    print(buckets.value_counts(dropna=False).sort_index())


def split_dataframe(
    df: pd.DataFrame,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shuffled = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train_df = shuffled.iloc[:n_train].copy()
    val_df = shuffled.iloc[n_train : n_train + n_val].copy()
    test_df = shuffled.iloc[n_train + n_val :].copy()
    return train_df, val_df, test_df


def build_features(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str], pd.Series, pd.Series]:
    feature_cols = [
        col
        for col in train_df.columns
        if col not in TARGET_COLS and col not in ID_OR_LEAKAGE_COLS
    ]

    combined = pd.concat(
        [
            train_df[feature_cols].assign(_split="train"),
            val_df[feature_cols].assign(_split="val"),
            test_df[feature_cols].assign(_split="test"),
        ],
        axis=0,
        ignore_index=True,
    )
    split_col = combined.pop("_split")

    categorical_cols = combined.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    encoded = pd.get_dummies(combined, columns=categorical_cols, dummy_na=True)
    encoded = encoded.replace([np.inf, -np.inf], np.nan).fillna(0)

    train_mask = split_col.eq("train").to_numpy()
    val_mask = split_col.eq("val").to_numpy()
    test_mask = split_col.eq("test").to_numpy()

    x_train_df = encoded.loc[train_mask].copy()
    x_val_df = encoded.loc[val_mask].copy()
    x_test_df = encoded.loc[test_mask].copy()

    means = x_train_df.mean()
    stds = x_train_df.std().replace(0, 1)

    x_train = ((x_train_df - means) / stds).astype("float32")
    x_val = ((x_val_df - means) / stds).astype("float32")
    x_test = ((x_test_df - means) / stds).astype("float32")

    return (
        torch.tensor(x_train.to_numpy(), dtype=torch.float32),
        torch.tensor(x_val.to_numpy(), dtype=torch.float32),
        torch.tensor(x_test.to_numpy(), dtype=torch.float32),
        x_train.columns.tolist(),
        means,
        stds,
    )


def build_targets(df: pd.DataFrame) -> torch.Tensor:
    y = df[TARGET_COLS].copy()
    y["vuelve_a_comprar"] = y["vuelve_a_comprar"].clip(0, 1)
    y["dias_hasta_proxima_compra"] = y["dias_hasta_proxima_compra"].clip(lower=0)
    y["target_potencial_cliente"] = y["target_potencial_cliente"].clip(-1, 1)
    return torch.tensor(y.to_numpy(dtype=np.float32), dtype=torch.float32)


def compute_loss(pred: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    bce = nn.functional.binary_cross_entropy(pred[:, 0], target[:, 0])
    days = nn.functional.smooth_l1_loss(torch.log1p(pred[:, 1]), torch.log1p(target[:, 1]))
    potential = nn.functional.mse_loss(pred[:, 2], target[:, 2])
    total = bce + days + potential
    return total, {
        "loss": float(total.detach().cpu()),
        "bce_recompra": float(bce.detach().cpu()),
        "huber_log_dias": float(days.detach().cpu()),
        "mse_potencial": float(potential.detach().cpu()),
    }


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_batches = 0
    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device)
        y_batch = y_batch.to(device)
        pred = model(x_batch)
        _, metrics = compute_loss(pred, y_batch)
        for key, value in metrics.items():
            totals[key] = totals.get(key, 0.0) + value
        n_batches += 1
    return {key: value / max(n_batches, 1) for key, value in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("dataset_modelo.csv"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = pd.read_csv(args.csv)
    missing_targets = [col for col in TARGET_COLS if col not in df.columns]
    if missing_targets:
        raise ValueError(f"Missing target columns: {missing_targets}")

    df = df.dropna(subset=TARGET_COLS).reset_index(drop=True)
    print(f"Loaded dataset: {args.csv} rows={len(df):,} columns={len(df.columns):,}")
    print_target_analysis(df)

    train_df, val_df, test_df = split_dataframe(df, seed=args.seed)
    print(
        "\nSplit sizes: "
        f"train={len(train_df):,} ({len(train_df) / len(df):.1%}), "
        f"val={len(val_df):,} ({len(val_df) / len(df):.1%}), "
        f"test={len(test_df):,} ({len(test_df) / len(df):.1%})"
    )

    x_train, x_val, x_test, feature_names, _, _ = build_features(train_df, val_df, test_df)
    y_train = build_targets(train_df)
    y_val = build_targets(val_df)
    y_test = build_targets(test_df)

    print(f"Input size after encoding: {x_train.shape[1]}")
    print(f"First 20 features: {feature_names[:20]}")

    train_loader = DataLoader(
        TensorDataset(x_train, y_train),
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(TensorDataset(x_val, y_val), batch_size=args.batch_size)
    test_loader = DataLoader(TensorDataset(x_test, y_test), batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PurchaseModel(input_size=x_train.shape[1], hidden_size=32).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_totals: dict[str, float] = {}
        n_batches = 0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            pred = model(x_batch)
            loss, metrics = compute_loss(pred, y_batch)
            loss.backward()
            optimizer.step()

            for key, value in metrics.items():
                train_totals[key] = train_totals.get(key, 0.0) + value
            n_batches += 1

        train_metrics = {key: value / max(n_batches, 1) for key, value in train_totals.items()}
        val_metrics = evaluate(model, val_loader, device)
        print(
            f"Epoch {epoch:03d} "
            f"train_loss={train_metrics['loss']:.4f} "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_bce={val_metrics['bce_recompra']:.4f} "
            f"val_days={val_metrics['huber_log_dias']:.4f} "
            f"val_potential={val_metrics['mse_potencial']:.4f}"
        )

    test_metrics = evaluate(model, test_loader, device)
    print("\n=== Test metrics ===")
    for key, value in test_metrics.items():
        print(f"{key}: {value:.4f}")

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": x_train.shape[1],
            "feature_names": feature_names,
            "target_cols": TARGET_COLS,
        },
        "purchase_model.pt",
    )
    print("\nSaved model to purchase_model.pt")


if __name__ == "__main__":
    main()
