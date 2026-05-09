"""Shared utilities for InterHack IA training scripts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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

# Columns to apply log1p transform to (guards against missing columns, so both datasets are safe).
# dataset_modelo.csv columns
_SKEWED_OLD = [
    "Valores_H", "Unidades",
    "gasto_anual_real_cliente_producto_hasta_fecha", "gasto_anual_real_cliente_categoria_hasta_fecha",
    "gasto_cliente_30d_previo", "gasto_cliente_producto_30d_previo", "gasto_cliente_categoria_30d_previo",
    "gasto_cliente_90d_previo", "gasto_cliente_producto_90d_previo", "gasto_cliente_categoria_90d_previo",
    "gasto_cliente_180d_previo", "gasto_cliente_producto_180d_previo", "gasto_cliente_categoria_180d_previo",
    "gasto_cliente_365d_previo", "gasto_cliente_producto_365d_previo", "gasto_cliente_categoria_365d_previo",
    "numero_compras_anteriores_producto", "numero_compras_anteriores_cliente",
    "numero_compras_anteriores_cliente_otros_productos", "numero_devoluciones_anteriores_producto",
]
# dataset_modelo_previo.csv columns (z-score cols are intentionally excluded — can be negative)
_SKEWED_PREVIO = [
    "Valores_H", "Unidades",
    "gasto_anual_real_cliente_producto",
    "gasto_medio_anual_cliente_categoria_producto", "gasto_medio_anual_cliente_categoria",
    "numero_compras_anteriores_producto",
    "total_compras_cliente_otros_productos", "numero_devoluciones_producto",
    "tiempo_medio_recompra_dias", "std_recompra_dias",
    "tiempo_medio_entre_compras_dias", "std_entre_compras_dias",
    "n_anios_cliente_categoria",
]
SKEWED_COLS: list[str] = list(dict.fromkeys(_SKEWED_OLD + _SKEWED_PREVIO))  # deduplicated, order preserved


def parse_hidden_sizes(value: str) -> list[int]:
    try:
        sizes = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--hidden-sizes must be a comma-separated list of integers"
        ) from exc
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError(
            "--hidden-sizes must contain positive integers, e.g. 512,256,128,64"
        )
    return sizes


def print_target_analysis(df: pd.DataFrame) -> None:
    print("\n=== Target analysis ===")
    for col in TARGET_COLS:
        if col in df.columns:
            print(f"\n{col}")
            print(df[col].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))

    if "vuelve_a_comprar" in df.columns:
        print("\nvuelve_a_comprar value counts")
        print(df["vuelve_a_comprar"].value_counts(dropna=False).sort_index())

    if "target_potencial_cliente" in df.columns:
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
    extra_exclude: list[str] | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str], pd.Series, pd.Series]:
    """Build and standardise feature tensors from three splits.

    Args:
        train_df, val_df, test_df: DataFrames for each split.
        extra_exclude: additional columns to exclude from features (e.g. a
            single target column used in another model).

    Returns:
        (x_train, x_val, x_test, feature_names, means, stds)
    """
    exclude = set(TARGET_COLS) | set(ID_OR_LEAKAGE_COLS)
    if extra_exclude:
        exclude |= set(extra_exclude)

    feature_cols = [col for col in train_df.columns if col not in exclude]

    for col in SKEWED_COLS:
        if col in feature_cols:
            train_df[col] = np.log1p(train_df[col].clip(lower=0))
            val_df[col] = np.log1p(val_df[col].clip(lower=0))
            test_df[col] = np.log1p(test_df[col].clip(lower=0))

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


def make_dataloader(
    x: torch.Tensor,
    y: torch.Tensor,
    batch_size: int,
    shuffle: bool = False,
    num_workers: int = 0,
    pin_memory: bool = False,
) -> DataLoader:
    loader_kwargs: dict[str, Any] = {"num_workers": num_workers, "pin_memory": pin_memory}
    if num_workers > 0:
        loader_kwargs["persistent_workers"] = True
    return DataLoader(TensorDataset(x, y), batch_size=batch_size, shuffle=shuffle, **loader_kwargs)


def save_checkpoint(
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
    target_cols: list[str],
    test_metrics: dict[str, float] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint: dict[str, Any] = {
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
        "target_cols": target_cols,
        "config": config,
    }
    torch.save(checkpoint, path)


def make_json_safe_config(args: argparse.Namespace, hidden_sizes: list[int]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            config[key] = str(value)
        else:
            config[key] = value
    config["hidden_sizes"] = hidden_sizes
    return config


def get_device(device_arg: str) -> torch.device:
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(device_arg)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda was requested, but CUDA is not available")
    return device


def describe_device(device: torch.device) -> str:
    if device.type != "cuda":
        return "cpu"
    index = device.index if device.index is not None else torch.cuda.current_device()
    name = torch.cuda.get_device_name(index)
    capability = torch.cuda.get_device_capability(index)
    total_memory_gb = torch.cuda.get_device_properties(index).total_memory / (1024**3)
    return (
        f"cuda:{index} ({name}, compute {capability[0]}.{capability[1]}, "
        f"{total_memory_gb:.1f} GB VRAM)"
    )


def update_totals(totals: dict[str, float], metrics: dict[str, float], batch_size: int) -> None:
    for key, value in metrics.items():
        totals[key] = totals.get(key, 0.0) + value * batch_size


def finalize_totals(totals: dict[str, float], n_samples: int) -> dict[str, float]:
    denominator = max(n_samples, 1)
    return {key: value / denominator for key, value in totals.items()}


def build_trunk(input_size: int, hidden_sizes: list[int], dropout: float) -> tuple[nn.Sequential, int]:
    """Build shared MLP trunk: Linear → BatchNorm → SiLU → Dropout blocks.

    Returns:
        (trunk, out_features) where out_features is the size of the last hidden layer.
    """
    layers: list[nn.Module] = []
    in_features = input_size
    for hidden_size in hidden_sizes:
        layers.extend([
            nn.Linear(in_features, hidden_size),
            nn.BatchNorm1d(hidden_size),
            nn.SiLU(),
        ])
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        in_features = hidden_size
    return nn.Sequential(*layers), in_features
