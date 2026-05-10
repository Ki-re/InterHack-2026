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
from torch.utils.data import DataLoader, Dataset, TensorDataset

from pipeline_inferencia import (
    MAX_DAYS,
    RecompraModel,
    SequentialDaysModel,
    SequentialPotentialModel,
    add_days_features,
    build_feature_matrix,
    build_sequence_samples,
    prepare_sequence_frame,
)


TARGET_COLS = ["vuelve_a_comprar", "dias_hasta_proxima_compra", "target_potencial_cliente"]
ID_COLS = ["Num.Fact", "Fecha", "Id. Cliente", "Id. Producto"]
LEAKAGE_COLS = [
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]
INTERNAL_COLS = ["__dataset_source__", "__orig_index__", "target_class", "target_log_days", "target_aux"]
POTENCIAL_BINS = [-1.01, -0.5, -0.1, 0.1, 0.5, 1.01]


@dataclass(frozen=True)
class ModelReport:
    name: str
    objective: str
    architecture: str
    metric_name: str
    baseline: dict[str, float]
    rows: int
    top_variables: list[dict[str, float]]


class SequenceTargetDataset(Dataset):
    def __init__(
        self,
        features: np.ndarray,
        samples: list[Any],
        targets: np.ndarray,
        extra_targets: np.ndarray | None = None,
    ) -> None:
        self.features = features
        self.samples = samples
        self.targets = targets
        self.extra_targets = extra_targets

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, ...]:
        sample = self.samples[idx]
        x = self.features[sample.start_pos : sample.end_pos + 1]
        base = (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(sample.length, dtype=torch.long),
            torch.tensor(self.targets[sample.orig_index]),
        )
        if self.extra_targets is None:
            return base
        return (*base, torch.tensor(self.extra_targets[sample.orig_index]))


def collate_potential(batch: list[tuple[torch.Tensor, ...]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, y = zip(*batch)
    return nn.utils.rnn.pad_sequence(xs, batch_first=True), torch.stack(lengths), torch.stack(y).long()


def collate_days(batch: list[tuple[torch.Tensor, ...]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, y_days, y_aux = zip(*batch)
    return (
        nn.utils.rnn.pad_sequence(xs, batch_first=True),
        torch.stack(lengths),
        torch.stack(y_days).float(),
        torch.stack(y_aux).long(),
    )


def load_checkpoint(path: Path) -> dict[str, Any]:
    return torch.load(path, map_location="cpu", weights_only=False)


def sample_dataframe(df: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df.reset_index(drop=True)
    return df.sample(n=max_rows, random_state=seed).sort_index().reset_index(drop=True)


def feature_to_variable(feature_name: str, raw_variables: list[str]) -> str:
    if feature_name in raw_variables:
        return feature_name
    prefix_matches = [raw for raw in raw_variables if feature_name.startswith(f"{raw}_")]
    if prefix_matches:
        return max(prefix_matches, key=len)
    return feature_name


def aggregate_importance(
    feature_names: list[str],
    feature_scores: list[float],
    raw_variables: list[str],
    top_n: int,
) -> list[dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for feature, score in zip(feature_names, feature_scores):
        variable = feature_to_variable(feature, raw_variables)
        grouped.setdefault(variable, []).append(max(float(score), 0.0))

    rows = []
    for variable, scores in grouped.items():
        rows.append(
            {
                "variable": variable,
                "importance": float(np.sum(scores)),
                "max_feature_importance": float(np.max(scores)),
                "encoded_features": float(len(scores)),
            }
        )
    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows[:top_n]


def raw_variables_for(df: pd.DataFrame, include_dataset_source: bool, add_days_extra_features: bool) -> list[str]:
    frame = add_days_features(df) if add_days_extra_features else df.copy()
    excluded = set(TARGET_COLS) | set(ID_COLS) | set(LEAKAGE_COLS) | set(INTERNAL_COLS)
    variables = [col for col in frame.columns if col not in excluded]
    if include_dataset_source:
        variables.append("dataset_source")
    return variables


@torch.no_grad()
def evaluate_recompra(model: nn.Module, x: np.ndarray, y: np.ndarray, batch_size: int) -> dict[str, float]:
    model.eval()
    losses: list[float] = []
    preds: list[np.ndarray] = []
    loader = DataLoader(
        TensorDataset(torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)),
        batch_size=batch_size,
    )
    for x_batch, y_batch in loader:
        logits = model(x_batch)
        loss = nn.functional.binary_cross_entropy_with_logits(logits, y_batch, reduction="sum")
        losses.append(float(loss.cpu()))
        preds.append((torch.sigmoid(logits) >= 0.5).cpu().numpy())
    pred = np.concatenate(preds).astype(np.float32)
    labels = y.astype(np.float32)
    return {
        "bce": float(np.sum(losses) / max(len(y), 1)),
        "accuracy": float(np.mean(pred == labels)),
    }


def report_recompra(df: pd.DataFrame, model_path: Path, batch_size: int, seed: int, top_n: int) -> ModelReport:
    checkpoint = load_checkpoint(model_path)
    config = checkpoint.get("config", {})
    model = RecompraModel(
        checkpoint["input_size"],
        config.get("hidden_sizes", [512, 256, 128]),
        float(config.get("dropout", 0.25)),
    )
    model.load_state_dict(checkpoint["model_state_dict"])

    frame = df.dropna(subset=["vuelve_a_comprar"]).reset_index(drop=True)
    x = build_feature_matrix(frame, checkpoint, include_dataset_source=False)
    y = frame["vuelve_a_comprar"].clip(0, 1).to_numpy(dtype=np.float32)
    baseline = evaluate_recompra(model, x, y, batch_size)

    rng = np.random.default_rng(seed)
    scores = []
    for idx in range(x.shape[1]):
        x_perm = x.copy()
        x_perm[:, idx] = rng.permutation(x_perm[:, idx])
        score = evaluate_recompra(model, x_perm, y, batch_size)["bce"] - baseline["bce"]
        scores.append(float(score))

    return ModelReport(
        name="fuga_model.pt",
        objective="Estimar la probabilidad de que el cliente no vuelva a comprar a partir del modelo binario de recompra.",
        architecture="Red neuronal feed-forward con capas densas, BatchNorm, activacion SiLU y dropout; salida logit binaria.",
        metric_name="incremento_bce",
        baseline=baseline,
        rows=len(frame),
        top_variables=aggregate_importance(
            list(checkpoint["feature_names"]),
            scores,
            raw_variables_for(frame, include_dataset_source=False, add_days_extra_features=False),
            top_n,
        ),
    )


@torch.no_grad()
def evaluate_potential(model: nn.Module, features: np.ndarray, samples: list[Any], y: np.ndarray, batch_size: int) -> dict[str, float]:
    model.eval()
    dataset = SequenceTargetDataset(features, samples, y)
    loader = DataLoader(dataset, batch_size=batch_size, collate_fn=collate_potential)
    total_loss = 0.0
    total_correct = 0
    total = 0
    for x_batch, lengths, y_batch in loader:
        logits = model(x_batch, lengths)
        total_loss += float(nn.functional.cross_entropy(logits, y_batch, reduction="sum").cpu())
        total_correct += int((logits.argmax(dim=1) == y_batch).sum().cpu())
        total += int(y_batch.numel())
    return {"cross_entropy": total_loss / max(total, 1), "accuracy": total_correct / max(total, 1)}


def report_potential(df: pd.DataFrame, model_path: Path, batch_size: int, seed: int, top_n: int) -> ModelReport:
    checkpoint = load_checkpoint(model_path)
    frame = df.dropna(subset=["target_potencial_cliente"]).reset_index(drop=True)
    sorted_frame = prepare_sequence_frame(frame, frame.attrs.get("dataset_source", "dataset"))
    features = build_feature_matrix(sorted_frame, checkpoint, include_dataset_source=True)
    y = pd.cut(
        frame["target_potencial_cliente"].clip(-1, 1),
        bins=POTENCIAL_BINS,
        labels=False,
        include_lowest=True,
    ).astype("int64").to_numpy()
    samples = build_sequence_samples(sorted_frame, checkpoint["max_seq_len"])

    class_names = checkpoint.get("potencial_class_names", ["muy_negativo", "negativo", "estable", "positivo", "muy_positivo"])
    model = SequentialPotentialModel(
        checkpoint["input_size"],
        checkpoint["hidden_size"],
        checkpoint["num_layers"],
        checkpoint["dropout"],
        len(class_names),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    baseline = evaluate_potential(model, features, samples, y, batch_size)

    rng = np.random.default_rng(seed)
    scores = []
    for idx in range(features.shape[1]):
        permuted = features.copy()
        permuted[:, idx] = rng.permutation(permuted[:, idx])
        score = evaluate_potential(model, permuted, samples, y, batch_size)["cross_entropy"] - baseline["cross_entropy"]
        scores.append(float(score))

    return ModelReport(
        name="potencial_model.pt",
        objective="Clasificar el potencial futuro del cliente-producto en cinco clases ordenadas y convertirlo en score 0-100.",
        architecture="Modelo secuencial GRU que resume el historial cliente-producto y aplica una cabeza densa multiclase.",
        metric_name="incremento_cross_entropy",
        baseline=baseline,
        rows=len(samples),
        top_variables=aggregate_importance(
            list(checkpoint["feature_names"]),
            scores,
            raw_variables_for(sorted_frame, include_dataset_source=True, add_days_extra_features=False),
            top_n,
        ),
    )


@torch.no_grad()
def evaluate_days(
    model: nn.Module,
    features: np.ndarray,
    samples: list[Any],
    y_days_log: np.ndarray,
    y_aux: np.ndarray,
    batch_size: int,
    aux_loss_weight: float,
) -> dict[str, float]:
    model.eval()
    dataset = SequenceTargetDataset(features, samples, y_days_log, y_aux)
    loader = DataLoader(dataset, batch_size=batch_size, collate_fn=collate_days)
    total_loss = 0.0
    total_mae = 0.0
    total = 0
    for x_batch, lengths, y_days_batch, y_aux_batch in loader:
        pred_log_days, aux_logits = model(x_batch, lengths)
        huber = nn.functional.smooth_l1_loss(pred_log_days, y_days_batch, reduction="sum")
        aux = nn.functional.cross_entropy(aux_logits, y_aux_batch, reduction="sum")
        total_loss += float((huber + aux_loss_weight * aux).cpu())
        pred_days = torch.expm1(pred_log_days).clamp(0, MAX_DAYS)
        real_days = torch.expm1(y_days_batch).clamp(0, MAX_DAYS)
        total_mae += float(torch.abs(pred_days - real_days).sum().cpu())
        total += int(y_days_batch.numel())
    return {"loss": total_loss / max(total, 1), "mae_days": total_mae / max(total, 1)}


def report_days(df: pd.DataFrame, model_path: Path, batch_size: int, seed: int, top_n: int) -> ModelReport:
    checkpoint = load_checkpoint(model_path)
    frame = df.dropna(subset=["dias_hasta_proxima_compra"]).reset_index(drop=True)
    sorted_frame = prepare_sequence_frame(frame, frame.attrs.get("dataset_source", "dataset"))
    features = build_feature_matrix(sorted_frame, checkpoint, include_dataset_source=True, add_days_extra_features=True)
    y_days = frame["dias_hasta_proxima_compra"].clip(0, MAX_DAYS).to_numpy(dtype=np.float32)
    y_days_log = np.log1p(y_days).astype(np.float32)
    months = (pd.to_datetime(frame["Fecha"], errors="coerce") + pd.to_timedelta(np.rint(y_days), unit="D")).dt.month
    y_aux = months.fillna(0).astype("int64").to_numpy()
    samples = build_sequence_samples(sorted_frame, checkpoint["max_seq_len"])

    aux_class_names = checkpoint.get("aux_class_names", [f"mes_{idx:02d}" for idx in range(13)])
    model = SequentialDaysModel(
        checkpoint["input_size"],
        len(aux_class_names),
        checkpoint["hidden_size"],
        checkpoint["num_layers"],
        checkpoint["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    aux_loss_weight = float(checkpoint.get("aux_loss_weight", 0.35))
    baseline = evaluate_days(model, features, samples, y_days_log, y_aux, batch_size, aux_loss_weight)

    rng = np.random.default_rng(seed)
    scores = []
    for idx in range(features.shape[1]):
        permuted = features.copy()
        permuted[:, idx] = rng.permutation(permuted[:, idx])
        score = evaluate_days(model, permuted, samples, y_days_log, y_aux, batch_size, aux_loss_weight)["loss"] - baseline["loss"]
        scores.append(float(score))

    return ModelReport(
        name="dias_model.pt",
        objective="Predecir los dias hasta la proxima compra y una clase auxiliar de mes de recompra.",
        architecture="Modelo secuencial GRU con una representacion compartida y dos cabezas: regresion de dias en escala log y clasificacion auxiliar.",
        metric_name="incremento_loss",
        baseline=baseline,
        rows=len(samples),
        top_variables=aggregate_importance(
            list(checkpoint["feature_names"]),
            scores,
            raw_variables_for(sorted_frame, include_dataset_source=True, add_days_extra_features=True),
            top_n,
        ),
    )


def render_markdown(reports: list[ModelReport], dataset_path: Path, sample_rows: int) -> str:
    lines = [
        "# IA",
        "",
        "Esta carpeta contiene los modelos de inferencia para scoring comercial sobre cliente-producto.",
        "El reporte se genera con `model_feature_importance.py` a partir de los modelos guardados y calcula explicabilidad por importancia de permutacion.",
        "",
        "## Como regenerar el reporte",
        "",
        "```powershell",
        "conda run -n interhack python IA/model_feature_importance.py --dataset IA/dataset.csv --write-readme",
        "```",
        "",
        "La importancia mide cuanto empeora la metrica del modelo al desordenar una variable. Valores mayores indican que el modelo depende mas de esa variable.",
        f"Dataset analizado: `{dataset_path.as_posix()}`. Filas muestreadas por modelo: `{sample_rows if sample_rows > 0 else 'todas'}`.",
        "",
        "## Modelos",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"### {report.name}",
                "",
                f"- Objetivo: {report.objective}",
                f"- Arquitectura: {report.architecture}",
                f"- Metrica de importancia: `{report.metric_name}`.",
                f"- Muestra evaluada: {report.rows:,} ejemplos.",
                f"- Baseline: {', '.join(f'{key}={value:.4f}' for key, value in report.baseline.items())}.",
                "",
                "| Variable | Importancia | Max. feature | Features codificadas |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in report.top_variables:
            lines.append(
                f"| {row['variable']} | {row['importance']:.6f} | "
                f"{row['max_feature_importance']:.6f} | {int(row['encoded_features'])} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Notas de interpretacion",
            "",
            "- La explicabilidad es global sobre la muestra usada, no una explicacion individual por prediccion.",
            "- Las variables categoricas se agregan desde sus columnas one-hot para que el ranking sea legible por variable original.",
            "- Las columnas objetivo, identificadores y variables de fuga temporal se excluyen de las entradas del modelo.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute permutation feature importance for IA models")
    parser.add_argument("--dataset", type=Path, default=Path("IA/dataset.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("IA/models"))
    parser.add_argument("--output-json", type=Path, default=Path("IA/feature_importance_report.json"))
    parser.add_argument("--output-md", type=Path, default=Path("IA/feature_importance_report.md"))
    parser.add_argument("--readme", type=Path, default=Path("IA/README.md"))
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--write-readme", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset)
    df.attrs["dataset_source"] = args.dataset.stem
    sampled = sample_dataframe(df, args.max_rows, args.seed)
    sampled.attrs["dataset_source"] = args.dataset.stem

    reports = [
        report_recompra(sampled, args.models_dir / "fuga_model.pt", args.batch_size, args.seed, args.top_n),
        report_potential(sampled, args.models_dir / "potencial_model.pt", args.batch_size, args.seed, args.top_n),
        report_days(sampled, args.models_dir / "dias_model.pt", args.batch_size, args.seed, args.top_n),
    ]

    payload = {
        "dataset": str(args.dataset),
        "max_rows": args.max_rows,
        "reports": [
            {
                "name": report.name,
                "objective": report.objective,
                "architecture": report.architecture,
                "metric_name": report.metric_name,
                "baseline": report.baseline,
                "rows": report.rows,
                "top_variables": report.top_variables,
            }
            for report in reports
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    markdown = render_markdown(reports, args.dataset, args.max_rows)
    args.output_md.write_text(markdown, encoding="utf-8")
    if args.write_readme:
        args.readme.write_text(markdown, encoding="utf-8")

    print(f"JSON report: {args.output_json}")
    print(f"Markdown report: {args.output_md}")
    if args.write_readme:
        print(f"README updated: {args.readme}")


if __name__ == "__main__":
    main()
