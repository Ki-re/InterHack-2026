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


class LargePurchaseModel(nn.Module):
    """Deeper MLP for tabular purchase prediction with constrained outputs."""

    def __init__(
        self,
        input_size: int,
        hidden_sizes: list[int],
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        if not hidden_sizes:
            raise ValueError("hidden_sizes must contain at least one layer")

        layers: list[nn.Module] = []
        in_features = input_size
        for hidden_size in hidden_sizes:
            layers.extend(
                [
                    nn.Linear(in_features, hidden_size),
                    nn.BatchNorm1d(hidden_size),
                    nn.SiLU(),
                ]
            )
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_features = hidden_size

        self.net = nn.Sequential(*layers)
        
        head_hidden = max(in_features // 2, 16)
        
        self.head_recompra = nn.Sequential(
            nn.Linear(in_features, head_hidden),
            nn.BatchNorm1d(head_hidden),
            nn.SiLU(),
            nn.Linear(head_hidden, 1)
        )
        
        self.head_days = nn.Sequential(
            nn.Linear(in_features, head_hidden),
            nn.BatchNorm1d(head_hidden),
            nn.SiLU(),
            nn.Linear(head_hidden, 1)
        )
        
        self.head_potential = nn.Sequential(
            nn.Linear(in_features, head_hidden),
            nn.BatchNorm1d(head_hidden),
            nn.SiLU(),
            nn.Linear(head_hidden, 1)
        )
        
        self.positive = nn.Softplus()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.net(x)
        raw_recompra = self.head_recompra(features).squeeze(1)
        raw_days = self.head_days(features).squeeze(1)
        raw_potential = self.head_potential(features).squeeze(1)
        
        return torch.stack(
            [
                torch.sigmoid(raw_recompra),
                self.positive(raw_days),
                torch.tanh(raw_potential),
            ],
            dim=1,
        )


def parse_hidden_sizes(value: str) -> list[int]:
    try:
        sizes = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--hidden-sizes must be a comma-separated list of integers"
        ) from exc

    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError(
            "--hidden-sizes must contain positive integers, for example 512,256,128,64"
        )
    return sizes


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
    
    # Apply log1p to known highly skewed columns if they exist
    skewed_cols = [
        "gasto_anual_real_cliente_producto", "gasto_medio_anual_cliente_categoria_producto",
        "numero_devoluciones_producto", "Valores_H", "numero_compras_anteriores_producto",
        "total_compras_cliente_otros_productos", "gasto_medio_anual_cliente_categoria",
        "Unidades"
    ]
    
    for col in skewed_cols:
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


def build_targets(df: pd.DataFrame) -> torch.Tensor:
    y = df[TARGET_COLS].copy()
    y["vuelve_a_comprar"] = y["vuelve_a_comprar"].clip(0, 1)
    y["dias_hasta_proxima_compra"] = y["dias_hasta_proxima_compra"].clip(lower=0)
    y["target_potencial_cliente"] = y["target_potencial_cliente"].clip(-1, 1)
    return torch.tensor(y.to_numpy(dtype=np.float32), dtype=torch.float32)


def compute_loss(pred: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    bce = nn.functional.binary_cross_entropy(pred[:, 0], target[:, 0])
    
    # Masked days loss: only compute where vuelve_a_comprar == 1
    mask = target[:, 0] == 1
    if mask.sum() > 0:
        days = nn.functional.smooth_l1_loss(torch.log1p(pred[mask, 1]), torch.log1p(target[mask, 1]))
    else:
        days = torch.tensor(0.0, device=pred.device)
        
    potential = nn.functional.mse_loss(pred[:, 2], target[:, 2])
    total = bce + days + potential
    return total, {
        "loss": float(total.detach().cpu()),
        "bce_recompra": float(bce.detach().cpu()),
        "huber_log_dias": float(days.detach().cpu()),
        "mse_potencial": float(potential.detach().cpu()),
    }


@torch.no_grad()
def compute_accuracy_metrics(
    pred: torch.Tensor,
    target: torch.Tensor,
    days_tolerance: float,
    potential_tolerance: float,
) -> dict[str, float]:
    recompra_target = target[:, 0].round().clamp(0, 1)
    recompra_pred = (pred[:, 0] >= 0.5).float()
    acc_recompra = (recompra_pred == recompra_target).float().mean()
    
    # Masked days accuracy
    mask = target[:, 0] == 1
    if mask.sum() > 0:
        acc_dias_pm3 = (torch.abs(pred[mask, 1] - target[mask, 1]) <= days_tolerance).float().mean()
        acc_dias_pct10 = (torch.abs(pred[mask, 1] - target[mask, 1]) <= 0.10 * target[mask, 1]).float().mean()
    else:
        acc_dias_pm3 = torch.tensor(0.0, device=pred.device)
        acc_dias_pct10 = torch.tensor(0.0, device=pred.device)
        
    acc_potencial_pm02 = (
        torch.abs(pred[:, 2] - target[:, 2]) <= potential_tolerance
    ).float().mean()
    return {
        "acc_recompra": float(acc_recompra.detach().cpu()),
        "acc_dias_pm3": float(acc_dias_pm3.detach().cpu()),
        "acc_dias_pct10": float(acc_dias_pct10.detach().cpu()),
        "acc_potencial_pm02": float(acc_potencial_pm02.detach().cpu()),
    }


def update_totals(
    totals: dict[str, float],
    metrics: dict[str, float],
    batch_size: int,
) -> None:
    for key, value in metrics.items():
        totals[key] = totals.get(key, 0.0) + value * batch_size


def finalize_totals(totals: dict[str, float], n_samples: int) -> dict[str, float]:
    denominator = max(n_samples, 1)
    return {key: value / denominator for key, value in totals.items()}


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    days_tolerance: float,
    potential_tolerance: float,
) -> dict[str, float]:
    model.eval()
    totals: dict[str, float] = {}
    n_samples = 0
    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device, non_blocking=True)
        y_batch = y_batch.to(device, non_blocking=True)
        pred = model(x_batch)
        _, loss_metrics = compute_loss(pred, y_batch)
        accuracy_metrics = compute_accuracy_metrics(
            pred,
            y_batch,
            days_tolerance=days_tolerance,
            potential_tolerance=potential_tolerance,
        )
        batch_size = x_batch.size(0)
        update_totals(totals, {**loss_metrics, **accuracy_metrics}, batch_size)
        n_samples += batch_size
    return finalize_totals(totals, n_samples)


def make_json_safe_config(args: argparse.Namespace, hidden_sizes: list[int]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            config[key] = str(value)
        else:
            config[key] = value
    config["hidden_sizes"] = hidden_sizes
    return config


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
        "target_cols": TARGET_COLS,
        "config": config,
    }
    torch.save(checkpoint, path)


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("IA/dataset_modelo.csv"))
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-sizes", type=parse_hidden_sizes, default=parse_hidden_sizes("512,256,128,64"))
    parser.add_argument("--dropout", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="cuda")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("IA/checkpoints_large"))
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--metric-days-tolerance", type=float, default=3.0)
    parser.add_argument("--metric-potential-tolerance", type=float, default=0.2)
    parser.add_argument("--sample-rows", type=int, default=0)
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    df = pd.read_csv(args.csv)
    missing_targets = [col for col in TARGET_COLS if col not in df.columns]
    if missing_targets:
        raise ValueError(f"Missing target columns: {missing_targets}")

    df = df.dropna(subset=TARGET_COLS).reset_index(drop=True)
    
    # Extracción de características temporales
    if "Fecha" in df.columns:
        fecha_dt = pd.to_datetime(df["Fecha"], errors="coerce")
        df["mes"] = fecha_dt.dt.month.fillna(1)
        df["dia_semana"] = fecha_dt.dt.dayofweek.fillna(0)
        
        # Codificación cíclica
        df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12.0)
        df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12.0)
        df["dia_semana_sin"] = np.sin(2 * np.pi * df["dia_semana"] / 7.0)
        df["dia_semana_cos"] = np.cos(2 * np.pi * df["dia_semana"] / 7.0)
        
    # Variables de interacción
    if "dias_desde_compra_anterior_producto" in df.columns and "tiempo_medio_entre_compras_dias" in df.columns:
        df["ratio_ciclo_compra"] = df["dias_desde_compra_anterior_producto"] / (df["tiempo_medio_entre_compras_dias"] + 1.0)
        
    if "numero_compras_anteriores_producto" in df.columns:
        df["is_first_purchase"] = (df["numero_compras_anteriores_producto"] == 0).astype(int)
        
    if "dias_desde_compra_anterior_producto" in df.columns and "tiempo_medio_recompra_dias" in df.columns:
        df["ratio_recencia_media"] = df["dias_desde_compra_anterior_producto"] / (df["tiempo_medio_recompra_dias"] + 1.0)
        
    if "gasto_anual_real_cliente_producto" in df.columns and "gasto_medio_anual_cliente_categoria" in df.columns:
        df["ratio_gasto_categoria"] = df["gasto_anual_real_cliente_producto"] / (df["gasto_medio_anual_cliente_categoria"] + 1.0)

    if args.sample_rows > 0:
        if args.sample_rows >= len(df):
            print(f"--sample-rows={args.sample_rows:,} >= dataset rows; using full dataset")
        else:
            df = df.sample(n=args.sample_rows, random_state=args.seed).reset_index(drop=True)
            print(f"Using sampled dataset: rows={len(df):,}")

    print(f"Loaded dataset: {args.csv} rows={len(df):,} columns={len(df.columns):,}")
    print_target_analysis(df)

    train_df, val_df, test_df = split_dataframe(df, seed=args.seed)
    print(
        "\nSplit sizes: "
        f"train={len(train_df):,} ({len(train_df) / len(df):.1%}), "
        f"val={len(val_df):,} ({len(val_df) / len(df):.1%}), "
        f"test={len(test_df):,} ({len(test_df) / len(df):.1%})"
    )

    x_train, x_val, x_test, feature_names, feature_means, feature_stds = build_features(
        train_df,
        val_df,
        test_df,
    )
    y_train = build_targets(train_df)
    y_val = build_targets(val_df)
    y_test = build_targets(test_df)

    print(f"Input size after encoding: {x_train.shape[1]}")
    print(f"First 20 features: {feature_names[:20]}")
    print(f"Hidden sizes: {args.hidden_sizes}")

    device = get_device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    pin_memory = device.type == "cuda"
    loader_kwargs = {
        "num_workers": args.num_workers,
        "pin_memory": pin_memory,
    }
    if args.num_workers > 0:
        loader_kwargs["persistent_workers"] = True

    train_loader = DataLoader(
        TensorDataset(x_train, y_train),
        batch_size=args.batch_size,
        shuffle=True,
        **loader_kwargs,
    )
    val_loader = DataLoader(
        TensorDataset(x_val, y_val),
        batch_size=args.batch_size,
        **loader_kwargs,
    )
    test_loader = DataLoader(
        TensorDataset(x_test, y_test),
        batch_size=args.batch_size,
        **loader_kwargs,
    )

    model = LargePurchaseModel(
        input_size=x_train.shape[1],
        hidden_sizes=args.hidden_sizes,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=8,
        min_lr=1e-6,
    )

    amp_enabled = args.amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    config = make_json_safe_config(args, args.hidden_sizes)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config_path = args.checkpoint_dir / "run_config.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Device: {describe_device(device)}")
    print(f"AMP enabled: {amp_enabled}")
    print(f"Checkpoint dir: {args.checkpoint_dir}")

    best_val_loss = float("inf")
    best_epoch = 0
    last_train_metrics: dict[str, float] = {}
    last_val_metrics: dict[str, float] = {}

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_totals: dict[str, float] = {}
        n_train_samples = 0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda", enabled=amp_enabled):
                pred = model(x_batch)
                loss, loss_metrics = compute_loss(pred, y_batch)

            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
            scaler.step(optimizer)
            scaler.update()

            batch_size = x_batch.size(0)
            update_totals(train_totals, loss_metrics, batch_size)
            n_train_samples += batch_size

        train_metrics = finalize_totals(train_totals, n_train_samples)
        val_metrics = evaluate(
            model,
            val_loader,
            device,
            days_tolerance=args.metric_days_tolerance,
            potential_tolerance=args.metric_potential_tolerance,
        )
        scheduler.step(val_metrics["loss"])
        current_lr = optimizer.param_groups[0]["lr"]

        last_train_metrics = train_metrics
        last_val_metrics = val_metrics
        improved = val_metrics["loss"] < best_val_loss
        if improved:
            best_val_loss = val_metrics["loss"]
            best_epoch = epoch
            save_checkpoint(
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
            save_checkpoint(
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
            f"lr={current_lr:.2e} "
            f"train_loss={train_metrics['loss']:.4f} "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_bce={val_metrics['bce_recompra']:.4f} "
            f"val_days={val_metrics['huber_log_dias']:.4f} "
            f"val_potential={val_metrics['mse_potencial']:.4f} "
            f"val_acc_recompra={val_metrics['acc_recompra']:.4f} "
            f"val_acc_dias_pm3={val_metrics['acc_dias_pm3']:.4f} "
            f"val_acc_dias_pct10={val_metrics['acc_dias_pct10']:.4f} "
            f"val_acc_potencial_pm02={val_metrics['acc_potencial_pm02']:.4f} "
            f"best_epoch={best_epoch:03d}"
        )

    test_metrics = evaluate(
        model,
        test_loader,
        device,
        days_tolerance=args.metric_days_tolerance,
        potential_tolerance=args.metric_potential_tolerance,
    )
    print("\n=== Test metrics ===")
    for key, value in test_metrics.items():
        print(f"{key}: {value:.4f}")

    save_checkpoint(
        args.checkpoint_dir / "last_model.pt",
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        epoch=args.epochs,
        train_metrics=last_train_metrics,
        val_metrics=last_val_metrics,
        test_metrics=test_metrics,
        feature_names=feature_names,
        feature_means=feature_means,
        feature_stds=feature_stds,
        config=config,
        best_val_loss=best_val_loss,
    )
    print(f"\nSaved best model to {args.checkpoint_dir / 'best_model.pt'}")
    print(f"Saved last model to {args.checkpoint_dir / 'last_model.pt'}")


if __name__ == "__main__":
    main()
