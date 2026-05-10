from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, TensorDataset


TARGET_COLS = ["vuelve_a_comprar", "dias_hasta_proxima_compra", "target_potencial_cliente"]
ID_COLS = ["Num.Fact", "Fecha", "Id. Cliente", "Provincia", "Id. Producto"]
LEAKAGE_COLS = [
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]
INTERNAL_COLS = ["__dataset_source__", "__orig_index__", "target_class", "target_log_days", "target_aux"]
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
MAX_DAYS = 365.0


class RecompraModel(nn.Module):
    def __init__(self, input_size: int, hidden_sizes: list[int], dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        in_features = input_size
        for hidden_size in hidden_sizes:
            layers.extend([nn.Linear(in_features, hidden_size), nn.BatchNorm1d(hidden_size), nn.SiLU()])
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_features = hidden_size
        self.trunk = nn.Sequential(*layers)
        self.head = nn.Linear(in_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.trunk(x)).squeeze(1)


class SequentialPotentialModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float, n_classes: int) -> None:
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
            nn.Linear(32, n_classes),
        )

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, hidden = self.gru(packed)
        return self.head(hidden[-1])


class SequentialDaysModel(nn.Module):
    def __init__(
        self,
        input_size: int,
        n_aux_classes: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
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
        packed = nn.utils.rnn.pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, hidden = self.gru(packed)
        features = self.shared(hidden[-1])
        pred_log_days = self.positive(self.days_head(features).squeeze(1))
        aux_logits = self.aux_head(features)
        return pred_log_days, aux_logits


@dataclass(frozen=True)
class SequenceSample:
    end_pos: int
    start_pos: int
    length: int
    orig_index: int


class SequenceInferenceDataset(Dataset):
    def __init__(self, features: np.ndarray, samples: list[SequenceSample]):
        self.features = features
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        x = self.features[sample.start_pos : sample.end_pos + 1]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(sample.length, dtype=torch.long),
            torch.tensor(sample.orig_index, dtype=torch.long),
        )


def collate_sequences(batch: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    xs, lengths, orig_indices = zip(*batch)
    padded = nn.utils.rnn.pad_sequence(xs, batch_first=True)
    return padded, torch.stack(lengths), torch.stack(orig_indices)


def to_series(value: Any, index: list[str]) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.reindex(index)
    return pd.Series(value).reindex(index)


def add_days_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    fecha = pd.to_datetime(df["Fecha"], errors="coerce") if "Fecha" in df.columns else pd.Series(pd.NaT, index=df.index)
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


def build_feature_matrix(
    df: pd.DataFrame,
    checkpoint: dict[str, Any],
    include_dataset_source: bool,
    add_days_extra_features: bool = False,
) -> np.ndarray:
    frame = add_days_features(df) if add_days_extra_features else df.copy()
    excluded = set(TARGET_COLS) | set(ID_COLS) | set(LEAKAGE_COLS) | set(INTERNAL_COLS)
    feature_cols = [col for col in frame.columns if col not in excluded]
    features = frame[feature_cols].copy()
    if include_dataset_source:
        features["dataset_source"] = frame["__dataset_source__"].astype("object")

    for col in SKEWED_COLS:
        if col in features.columns:
            features[col] = np.log1p(features[col].clip(lower=0))

    categorical_cols = features.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    encoded = pd.get_dummies(features, columns=categorical_cols, dummy_na=True)
    encoded = encoded.replace([np.inf, -np.inf], np.nan).fillna(0)

    feature_names = list(checkpoint["feature_names"])
    encoded = encoded.reindex(columns=feature_names, fill_value=0)
    means = to_series(checkpoint["feature_means"], feature_names).fillna(0)
    stds = to_series(checkpoint["feature_stds"], feature_names).replace(0, 1).fillna(1)
    normalized = ((encoded - means) / stds).astype("float32")
    return normalized.to_numpy(dtype=np.float32)


def prepare_sequence_frame(df: pd.DataFrame, dataset_source: str) -> pd.DataFrame:
    frame = df.copy()
    frame["__orig_index__"] = np.arange(len(frame), dtype=np.int64)
    frame["__dataset_source__"] = dataset_source
    frame["Fecha"] = pd.to_datetime(frame["Fecha"], errors="coerce")
    return frame.sort_values(
        ["__dataset_source__", "Id. Cliente", "Id. Producto", "Fecha", "Num.Fact", "__orig_index__"],
        kind="mergesort",
    ).reset_index(drop=True)


def build_sequence_samples(frame: pd.DataFrame, max_seq_len: int) -> list[SequenceSample]:
    samples: list[SequenceSample] = []
    for _, group in frame.groupby(["__dataset_source__", "Id. Cliente", "Id. Producto"], sort=False):
        positions = group.index.to_numpy()
        orig_indices = group["__orig_index__"].to_numpy(dtype=np.int64)
        for pos in range(len(group)):
            start_pos = max(0, pos - max_seq_len + 1)
            samples.append(
                SequenceSample(
                    end_pos=int(positions[pos]),
                    start_pos=int(positions[start_pos]),
                    length=int(pos - start_pos + 1),
                    orig_index=int(orig_indices[pos]),
                )
            )
    return samples


def infer_recompra(df: pd.DataFrame, checkpoint: dict[str, Any], device: torch.device, batch_size: int) -> np.ndarray:
    config = checkpoint.get("config", {})
    hidden_sizes = config.get("hidden_sizes", [512, 256, 128])
    dropout = float(config.get("dropout", 0.25))
    x = build_feature_matrix(df, checkpoint, include_dataset_source=False)
    model = RecompraModel(checkpoint["input_size"], hidden_sizes, dropout).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    scores: list[np.ndarray] = []
    loader = DataLoader(TensorDataset(torch.tensor(x, dtype=torch.float32)), batch_size=batch_size)
    with torch.no_grad():
        for (x_batch,) in loader:
            logits = model(x_batch.to(device))
            prob_recompra = torch.sigmoid(logits).detach().cpu().numpy()
            scores.append((1.0 - prob_recompra) * 100.0)
    return np.concatenate(scores).clip(0, 100)


def infer_potencial(
    sorted_frame: pd.DataFrame,
    checkpoint: dict[str, Any],
    device: torch.device,
    batch_size: int,
    n_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    features = build_feature_matrix(sorted_frame, checkpoint, include_dataset_source=True)
    samples = build_sequence_samples(sorted_frame, checkpoint["max_seq_len"])
    scores = np.full(n_rows, np.nan, dtype=np.float32)
    classes = np.full(n_rows, -1, dtype=np.int64)
    if not samples:
        return scores, classes

    class_names = checkpoint.get("potencial_class_names", ["muy_negativo", "negativo", "estable", "positivo", "muy_positivo"])
    model = SequentialPotentialModel(
        checkpoint["input_size"],
        checkpoint["hidden_size"],
        checkpoint["num_layers"],
        checkpoint["dropout"],
        len(class_names),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    weights = torch.linspace(0, 100, steps=len(class_names), device=device)
    loader = DataLoader(SequenceInferenceDataset(features, samples), batch_size=batch_size, collate_fn=collate_sequences)
    with torch.no_grad():
        for x_batch, lengths, orig_indices in loader:
            logits = model(x_batch.to(device), lengths.to(device))
            probs = torch.softmax(logits, dim=1)
            batch_scores = (probs * weights).sum(dim=1).detach().cpu().numpy()
            batch_classes = logits.argmax(dim=1).detach().cpu().numpy()
            idx = orig_indices.numpy()
            scores[idx] = batch_scores
            classes[idx] = batch_classes
    return scores.clip(0, 100), classes


def infer_dias(
    sorted_frame: pd.DataFrame,
    checkpoint: dict[str, Any],
    device: torch.device,
    batch_size: int,
    n_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    features = build_feature_matrix(sorted_frame, checkpoint, include_dataset_source=True, add_days_extra_features=True)
    samples = build_sequence_samples(sorted_frame, checkpoint["max_seq_len"])
    pred_days = np.full(n_rows, np.nan, dtype=np.float32)
    pred_aux = np.full(n_rows, -1, dtype=np.int64)
    if not samples:
        return pred_days, pred_aux

    aux_class_names = checkpoint.get("aux_class_names", [f"mes_{idx:02d}" for idx in range(13)])
    model = SequentialDaysModel(
        checkpoint["input_size"],
        len(aux_class_names),
        checkpoint["hidden_size"],
        checkpoint["num_layers"],
        checkpoint["dropout"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    loader = DataLoader(SequenceInferenceDataset(features, samples), batch_size=batch_size, collate_fn=collate_sequences)
    max_days = float(checkpoint.get("max_days", MAX_DAYS))
    with torch.no_grad():
        for x_batch, lengths, orig_indices in loader:
            pred_log_days, aux_logits = model(x_batch.to(device), lengths.to(device))
            days = torch.expm1(pred_log_days).clamp(0, max_days).detach().cpu().numpy()
            aux = aux_logits.argmax(dim=1).detach().cpu().numpy()
            idx = orig_indices.numpy()
            pred_days[idx] = days
            pred_aux[idx] = aux
    return pred_days, pred_aux


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    return torch.load(path, map_location="cpu", weights_only=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run inference over dataset.csv using trained models")
    parser.add_argument("--dataset", type=Path, default=Path("dataset.csv"))
    parser.add_argument("--recompra-model", type=Path, default=Path("models/fuga_model.pt"))
    parser.add_argument("--potencial-model", type=Path, default=Path("models/potencial_model.pt"))
    parser.add_argument("--dias-model", type=Path, default=Path("models/dias_model.pt"))
    parser.add_argument("--output", type=Path, default=Path("predicciones.csv"))
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--max-rows", type=int, default=0, help="Optional debug limit; 0 means all rows.")
    args = parser.parse_args()

    device = torch.device("cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu")
    df = pd.read_csv(args.dataset)
    if args.max_rows > 0:
        df = df.head(args.max_rows).copy()
    if "Fecha" not in df.columns:
        raise ValueError("dataset must include Fecha")

    print(f"Loaded {args.dataset}: rows={len(df):,} columns={len(df.columns):,}")
    print(f"Device: {device}")

    recompra_ckpt = load_checkpoint(args.recompra_model)
    potencial_ckpt = load_checkpoint(args.potencial_model)
    dias_ckpt = load_checkpoint(args.dias_model)

    output = df.copy()
    output["score_riesgo_0_100"] = infer_recompra(df, recompra_ckpt, device, args.batch_size)

    dataset_source = args.dataset.stem
    sorted_frame = prepare_sequence_frame(df, dataset_source)
    potencial_score, potencial_class_idx = infer_potencial(
        sorted_frame, potencial_ckpt, device, args.batch_size, len(df)
    )
    output["score_potencial_0_100"] = potencial_score
    potencial_names = potencial_ckpt.get("potencial_class_names", [])
    output["potencial_clase_predicha"] = [
        potencial_names[idx] if 0 <= idx < len(potencial_names) else pd.NA for idx in potencial_class_idx
    ]

    pred_days, pred_aux = infer_dias(sorted_frame, dias_ckpt, device, args.batch_size, len(df))
    output["prediccion_dias_hasta_proxima_compra"] = np.round(pred_days, 1)
    fechas = pd.to_datetime(output["Fecha"], errors="coerce")
    pred_dates = fechas + pd.to_timedelta(np.rint(pred_days), unit="D")
    output["prediccion_fecha_proxima_compra"] = pred_dates.dt.date.astype("string")
    output["prediccion_mes_proxima_compra"] = pred_dates.dt.to_period("M").astype("string")
    output["prediccion_dia_proxima_compra"] = pred_dates.dt.day.astype("Int64")

    aux_names = dias_ckpt.get("aux_class_names", [])
    output["prediccion_bucket_mes_modelo_dias"] = [
        aux_names[idx] if 0 <= idx < len(aux_names) else pd.NA for idx in pred_aux
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved predictions: {args.output}")
    print(f"Rows with potential prediction: {output['score_potencial_0_100'].notna().sum():,}/{len(output):,}")
    print(f"Rows with days prediction: {output['prediccion_dias_hasta_proxima_compra'].notna().sum():,}/{len(output):,}")


if __name__ == "__main__":
    main()
