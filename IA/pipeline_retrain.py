from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]
    log_file: Path
    outputs: list[Path]


IA_UTILS_SOURCE = r'''from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


TARGET_COLS = ["vuelve_a_comprar", "dias_hasta_proxima_compra", "target_potencial_cliente"]
ID_OR_LEAKAGE_COLS = [
    "Num.Fact",
    "Fecha",
    "Id. Cliente",
    "Provincia",
    "Id. Producto",
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]
SKEWED_COLS = [
    "Valores_H",
    "Unidades",
    "gasto_anual_real_cliente_producto",
    "gasto_medio_anual_cliente_categoria_producto",
    "gasto_medio_anual_cliente_categoria",
    "numero_compras_anteriores_producto",
    "total_compras_cliente_otros_productos",
    "numero_devoluciones_producto",
    "tiempo_medio_recompra_dias",
    "std_recompra_dias",
    "tiempo_medio_entre_compras_dias",
    "std_entre_compras_dias",
    "n_anios_cliente_categoria",
]


def parse_hidden_sizes(value: str) -> list[int]:
    try:
        sizes = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--hidden-sizes must be a comma-separated list of integers") from exc
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError("--hidden-sizes must contain positive integers")
    return sizes


def print_target_analysis(df: pd.DataFrame) -> None:
    print("\n=== Target analysis ===")
    for col in TARGET_COLS:
        if col in df.columns:
            print(f"\n{col}")
            print(df[col].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))


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
    return shuffled.iloc[:n_train].copy(), shuffled.iloc[n_train : n_train + n_val].copy(), shuffled.iloc[
        n_train + n_val :
    ].copy()


def build_features(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    extra_exclude: list[str] | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[str], pd.Series, pd.Series]:
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

    return (
        torch.tensor(((x_train_df - means) / stds).astype("float32").to_numpy(), dtype=torch.float32),
        torch.tensor(((x_val_df - means) / stds).astype("float32").to_numpy(), dtype=torch.float32),
        torch.tensor(((x_test_df - means) / stds).astype("float32").to_numpy(), dtype=torch.float32),
        x_train_df.columns.tolist(),
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
            "target_cols": target_cols,
            "config": config,
        },
        path,
    )


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
    return f"cuda:{index} ({torch.cuda.get_device_name(index)})"


def update_totals(totals: dict[str, float], metrics: dict[str, float], batch_size: int) -> None:
    for key, value in metrics.items():
        totals[key] = totals.get(key, 0.0) + value * batch_size


def finalize_totals(totals: dict[str, float], n_samples: int) -> dict[str, float]:
    return {key: value / max(n_samples, 1) for key, value in totals.items()}


def build_trunk(input_size: int, hidden_sizes: list[int], dropout: float) -> tuple[nn.Sequential, int]:
    layers: list[nn.Module] = []
    in_features = input_size
    for hidden_size in hidden_sizes:
        layers.extend([nn.Linear(in_features, hidden_size), nn.BatchNorm1d(hidden_size), nn.SiLU()])
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        in_features = hidden_size
    return nn.Sequential(*layers), in_features
'''


TRAIN_DIAS_COMMON_SOURCE = r'''from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import torch
from torch import nn


MODEL_TARGET = "dias_hasta_proxima_compra"
MAX_DAYS = 365.0
AuxTask = Literal["months", "ranges", "biweekly"]

AUX_CONFIG: dict[AuxTask, dict[str, Any]] = {
    "months": {
        "name": "mes_exacto",
        "class_names": [f"mes_{idx:02d}" for idx in range(13)],
        "target_col": "dias_mes_exacto_0_12",
    },
    "ranges": {
        "name": "tramo",
        "class_names": ["0_7", "8_14", "15_30", "31_60", "61_90", "91_180", "181_365", "365"],
        "bins": torch.tensor([7.0, 14.0, 30.0, 60.0, 90.0, 180.0, 364.999]),
        "target_col": "dias_tramo",
    },
    "biweekly": {
        "name": "bisemanal",
        "class_names": [f"b{idx:02d}" for idx in range(27)],
        "target_col": "dias_bisemanal_14d",
    },
}


def resolve_csv_path(path: Path) -> Path:
    if path.exists():
        return path
    if len(path.parts) > 1 and Path(path.name).exists():
        return Path(path.name)
    raise FileNotFoundError(f"Dataset not found: {path}")


def add_days_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Fecha" in df.columns:
        fecha = pd.to_datetime(df["Fecha"], errors="coerce")
        df["fecha_mes"] = fecha.dt.month.fillna(0).astype("int16")
        df["fecha_trimestre"] = fecha.dt.quarter.fillna(0).astype("int16")
        df["fecha_dia_semana"] = fecha.dt.dayofweek.fillna(0).astype("int16")
        day_of_year = fecha.dt.dayofyear.fillna(1).astype("float32")
        df["fecha_dia_anio_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
        df["fecha_dia_anio_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

    if {"dias_desde_compra_anterior_producto", "tiempo_medio_recompra_dias"}.issubset(df.columns):
        denom = df["tiempo_medio_recompra_dias"].replace(0, np.nan)
        df["ratio_recencia_vs_producto"] = (df["dias_desde_compra_anterior_producto"] / denom).replace(
            [np.inf, -np.inf], np.nan
        )

    if {"tiempo_medio_recompra_dias", "tiempo_medio_entre_compras_dias"}.issubset(df.columns):
        denom = df["tiempo_medio_entre_compras_dias"].replace(0, np.nan)
        df["ratio_recompra_vs_cliente"] = (df["tiempo_medio_recompra_dias"] / denom).replace(
            [np.inf, -np.inf], np.nan
        )

    return df


def build_aux_targets(days: np.ndarray, aux_task: AuxTask) -> torch.Tensor:
    days_tensor = torch.tensor(days, dtype=torch.float32).clamp(0, MAX_DAYS)
    if aux_task == "months":
        return torch.div(days_tensor, 30.4375, rounding_mode="floor").clamp(0, 12).long()
    if aux_task == "ranges":
        return torch.bucketize(days_tensor, AUX_CONFIG["ranges"]["bins"]).long()
    if aux_task == "biweekly":
        return torch.div(days_tensor, 14.0, rounding_mode="floor").clamp(0, 26).long()
    raise ValueError(f"Unsupported aux task: {aux_task}")


def macro_f1(pred_label: torch.Tensor, target_label: torch.Tensor, num_classes: int) -> float:
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
        f1s.append(float(f1.detach().cpu()))
    return float(np.mean(f1s))


def compute_loss(
    pred: tuple[torch.Tensor, torch.Tensor],
    target_log_days: torch.Tensor,
    target_aux: torch.Tensor,
    aux_loss_weight: float,
) -> tuple[torch.Tensor, dict[str, float]]:
    pred_log_days, aux_logits = pred
    days_loss = nn.functional.smooth_l1_loss(pred_log_days, target_log_days)
    aux_loss = nn.functional.cross_entropy(aux_logits, target_aux)
    loss = days_loss + aux_loss_weight * aux_loss
    return loss, {
        "loss": float(loss.detach().cpu()),
        "huber_log_dias": float(days_loss.detach().cpu()),
        "ce_aux": float(aux_loss.detach().cpu()),
    }


@torch.no_grad()
def compute_metrics(
    pred: tuple[torch.Tensor, torch.Tensor],
    target_log_days: torch.Tensor,
    target_aux: torch.Tensor,
    n_classes: int,
    days_tolerance_abs: float,
    days_tolerance_abs2: float,
) -> dict[str, float]:
    pred_log_days, aux_logits = pred
    pred_days = torch.expm1(pred_log_days).clamp(0, MAX_DAYS)
    target_days = torch.expm1(target_log_days).clamp(0, MAX_DAYS)
    diff = torch.abs(pred_days - target_days)
    pct_err = diff / target_days.clamp(min=1)
    pred_aux = aux_logits.argmax(dim=1)
    return {
        "mae_days": float(diff.mean().cpu()),
        "acc_dias_pm3": float((diff <= days_tolerance_abs).float().mean().cpu()),
        "acc_dias_pm20": float((diff <= days_tolerance_abs2).float().mean().cpu()),
        "acc_dias_pct10": float((pct_err <= 0.10).float().mean().cpu()),
        "acc_aux": float((pred_aux == target_aux).float().mean().cpu()),
        "f1_aux_macro": macro_f1(pred_aux, target_aux, n_classes),
    }
'''


def ensure_training_support_modules(cwd: Path, include_recompra: bool, include_dias: bool) -> None:
    modules: dict[str, str] = {}
    if include_recompra:
        modules["ia_utils.py"] = IA_UTILS_SOURCE
    if include_dias:
        modules["train_dias_common.py"] = TRAIN_DIAS_COMMON_SOURCE
    for filename, source in modules.items():
        path = cwd / filename
        path.write_text(source, encoding="utf-8")
        print(f"Prepared support module: {filename}")


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def require_files(paths: list[Path], cwd: Path) -> None:
    missing = [path for path in paths if not path.exists()]
    if missing:
        formatted = "\n".join(f"  - {rel(path, cwd)}" for path in missing)
        raise FileNotFoundError(f"Missing required files:\n{formatted}")


def run_step(step: Step, cwd: Path, dry_run: bool, continue_on_error: bool) -> dict[str, object]:
    printable = " ".join(str(part) for part in step.command)
    print(f"\n=== {step.name} ===")
    print(printable)

    result: dict[str, object] = {
        "name": step.name,
        "command": step.command,
        "log_file": str(step.log_file),
        "outputs": [str(path) for path in step.outputs],
        "returncode": None,
        "duration_seconds": 0.0,
    }
    if dry_run:
        result["returncode"] = 0
        return result

    step.log_file.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with step.log_file.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            step.command,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    duration = time.perf_counter() - start
    result["returncode"] = process.returncode
    result["duration_seconds"] = round(duration, 3)

    if process.returncode != 0:
        print(f"FAILED: {step.name} rc={process.returncode}. Log: {step.log_file}")
        if not continue_on_error:
            raise RuntimeError(f"Step failed: {step.name}. See {step.log_file}")
    else:
        print(f"OK: {step.name} ({duration:.1f}s). Log: {step.log_file}")
        for output in step.outputs:
            if output.exists():
                print(f"  output: {output}")
            else:
                print(f"  missing expected output: {output}")

    return result


def promote_checkpoint(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Cannot promote missing checkpoint: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"Promoted {source} -> {destination}")


def build_steps(args: argparse.Namespace, cwd: Path, run_dir: Path) -> list[Step]:
    py = sys.executable
    logs_dir = run_dir / "logs"

    steps: list[Step] = []
    if not args.skip_ingestion:
        steps.append(
            Step(
                name="ingestion",
                command=[
                    py,
                    "pipeline_ingestion_datos.py",
                    "--input",
                    str(args.input),
                    "--output",
                    str(args.dataset),
                ],
                log_file=logs_dir / "01_ingestion.log",
                outputs=[args.dataset],
            )
        )

    if not args.skip_recompra:
        steps.append(
            Step(
                name="train_recompra",
                command=[
                    py,
                    "train_recompra.py",
                    "--csv",
                    str(args.dataset),
                    "--epochs",
                    str(args.epochs_recompra),
                    "--batch-size",
                    str(args.batch_size_tabular),
                    "--checkpoint-dir",
                    str(args.checkpoints_dir / "recompra"),
                    "--checkpoint-every",
                    str(args.checkpoint_every),
                    "--device",
                    args.device,
                ],
                log_file=logs_dir / "02_train_recompra.log",
                outputs=[args.checkpoints_dir / "recompra" / "best_model.pt"],
            )
        )

    if not args.skip_potencial:
        steps.append(
            Step(
                name="train_potencial",
                command=[
                    py,
                    "train_potencial.py",
                    "--csv",
                    str(args.dataset),
                    "--output",
                    str(args.models_dir / "potential_model.pt"),
                    "--epochs",
                    str(args.epochs_potencial),
                    "--batch-size",
                    str(args.batch_size_sequential),
                ],
                log_file=logs_dir / "03_train_potencial.log",
                outputs=[args.models_dir / "potential_model.pt"],
            )
        )

    if not args.skip_dias:
        steps.append(
            Step(
                name="train_dias",
                command=[
                    py,
                    "train_.py",
                    "--csv",
                    str(args.dataset),
                    "--output",
                    str(args.models_dir / "dias_model.pt"),
                    "--checkpoint-dir",
                    str(args.checkpoints_dir / "dias"),
                    "--checkpoint-every",
                    str(args.checkpoint_every),
                    "--epochs",
                    str(args.epochs_dias),
                    "--batch-size",
                    str(args.batch_size_sequential),
                    "--aux-task",
                    args.dias_aux_task,
                ],
                log_file=logs_dir / "04_train_dias.log",
                outputs=[args.models_dir / "dias_model.pt", args.checkpoints_dir / "dias" / "best_model.pt"],
            )
        )

    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full data ingestion + model retraining pipeline")
    parser.add_argument("--input", type=Path, default=Path("Datasets.xlsx"))
    parser.add_argument("--dataset", type=Path, default=Path("dataset.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--checkpoints-dir", type=Path, default=Path("checkpoints"))
    parser.add_argument("--runs-dir", type=Path, default=Path("retrain_runs"))

    parser.add_argument("--epochs-recompra", type=int, default=250)
    parser.add_argument("--epochs-potencial", type=int, default=120)
    parser.add_argument("--epochs-dias", type=int, default=100)
    parser.add_argument("--batch-size-tabular", type=int, default=2048)
    parser.add_argument("--batch-size-sequential", type=int, default=1024)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--dias-aux-task", choices=["months", "ranges", "biweekly"], default="months")

    parser.add_argument("--skip-ingestion", action="store_true")
    parser.add_argument("--skip-recompra", action="store_true")
    parser.add_argument("--skip-potencial", action="store_true")
    parser.add_argument("--skip-dias", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--promote-recompra",
        action="store_true",
        help="Copy checkpoints/recompra/best_model.pt to models/fuga_model.pt after recompra training.",
    )
    return parser.parse_args()


def main() -> None:
    cwd = Path(__file__).resolve().parent
    os.chdir(cwd)
    args = parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    args.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    ensure_training_support_modules(
        cwd,
        include_recompra=not args.skip_recompra,
        include_dias=not args.skip_dias,
    )

    required = []
    if not args.skip_ingestion:
        required.extend([Path("pipeline_ingestion_datos.py"), args.input])
    if not args.skip_recompra:
        required.append(Path("train_recompra.py"))
    if not args.skip_potencial:
        required.append(Path("train_potencial.py"))
    if not args.skip_dias:
        required.append(Path("train_.py"))
    if args.skip_ingestion:
        required.append(args.dataset)
    require_files(required, cwd)

    steps = build_steps(args, cwd, run_dir)
    summary: dict[str, object] = {
        "run_id": run_id,
        "cwd": str(cwd),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "args": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "steps": [],
    }

    try:
        for step in steps:
            step_result = run_step(step, cwd, args.dry_run, args.continue_on_error)
            summary["steps"].append(step_result)

        if args.promote_recompra and not args.dry_run and not args.skip_recompra:
            promote_checkpoint(args.checkpoints_dir / "recompra" / "best_model.pt", args.models_dir / "fuga_model.pt")

        summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
        summary["status"] = "ok"
    except Exception as exc:
        summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
        summary["status"] = "failed"
        summary["error"] = str(exc)
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        raise

    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nPipeline summary: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
