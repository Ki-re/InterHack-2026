from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from train_secuencial import (
    POTENCIAL_CLASS_NAMES,
    SequentialPotentialModel,
    PotentialSequenceDataset,
    build_feature_frame,
    build_sequence_samples,
    collate_sequences,
    compute_loss,
    load_datasets,
    macro_precision_recall_f1,
    potential_to_class,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent


def resolve_path(path: Path) -> Path:
    if path.exists():
        return path

    candidates = []
    if not path.is_absolute():
        candidates.extend([PROJECT_ROOT / path, SCRIPT_DIR / path])

    # Handles Windows paths passed as "\IA\file.pt", which are rooted at the
    # drive instead of relative to the repository.
    stripped = str(path).lstrip("\\/")
    if stripped:
        stripped_path = Path(stripped)
        candidates.extend([PROJECT_ROOT / stripped_path, SCRIPT_DIR / stripped_path])

    candidates.extend([PROJECT_ROOT / path.name, SCRIPT_DIR / path.name])

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else path


def _checkpoint_mapping(value: object) -> pd.Series:
    if isinstance(value, pd.Series):
        return value
    if isinstance(value, dict):
        return pd.Series(value)
    raise TypeError(f"Unsupported checkpoint mapping type: {type(value)!r}")


def align_and_normalize_features(
    feature_frame: pd.DataFrame,
    feature_names: list[str],
    feature_means: pd.Series,
    feature_stds: pd.Series,
) -> np.ndarray:
    aligned = feature_frame.reindex(columns=feature_names, fill_value=0)
    means = feature_means.reindex(feature_names).fillna(0)
    stds = feature_stds.reindex(feature_names).replace(0, 1).fillna(1)
    normalized = ((aligned - means) / stds).replace([np.inf, -np.inf], np.nan).fillna(0)
    return normalized.astype("float32").to_numpy(dtype=np.float32)


@torch.no_grad()
def evaluate_full_dataset(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> tuple[dict[str, float], np.ndarray]:
    model.eval()
    totals: dict[str, float] = {}
    confusion = np.zeros((len(POTENCIAL_CLASS_NAMES), len(POTENCIAL_CLASS_NAMES)), dtype=np.int64)
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

        target_np = target.detach().cpu().numpy()
        pred_np = pred_label.detach().cpu().numpy()
        for true_class, pred_class in zip(target_np, pred_np):
            confusion[int(true_class), int(pred_class)] += 1

    return {key: value / max(n_batches, 1) for key, value in totals.items()}, confusion


def print_confusion(confusion: np.ndarray) -> None:
    print("\n=== Confusion matrix ===")
    header = "true\\pred," + ",".join(POTENCIAL_CLASS_NAMES)
    print(header)
    for idx, class_name in enumerate(POTENCIAL_CLASS_NAMES):
        row = ",".join(str(int(value)) for value in confusion[idx])
        print(f"{class_name},{row}")

    print("\n=== Per-class recall ===")
    for idx, class_name in enumerate(POTENCIAL_CLASS_NAMES):
        total = confusion[idx].sum()
        recall = confusion[idx, idx] / total if total else 0.0
        print(f"{class_name}: {recall:.4f} ({int(confusion[idx, idx])}/{int(total)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sequential potential model against the full dataset.")
    parser.add_argument("--model", type=Path, default=Path("IA/purchase_sequential_potential_model.pt"))
    parser.add_argument("--csv", type=Path, nargs="+", default=None)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    args = parser.parse_args()

    model_path = resolve_path(args.model)
    if not model_path.exists():
        available = ", ".join(path.name for path in SCRIPT_DIR.glob("*sequential*.pt")) or "none"
        raise FileNotFoundError(
            f"Model checkpoint not found: {model_path}. "
            "Train the potential sequential model first or pass --model with the checkpoint path. "
            f"Available sequential checkpoints in {SCRIPT_DIR}: {available}"
        )
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    csv_paths = args.csv or [Path(path) for path in checkpoint.get("csv_paths", [])]
    if not csv_paths:
        csv_paths = [Path("IA/dataset_modelo.csv"), Path("IA/dataset_modelo_previo.csv")]
    csv_paths = [resolve_path(path) for path in csv_paths]

    df = load_datasets(csv_paths)
    required = ["Fecha", "Id. Cliente", "Id. Producto", "target_potencial_cliente"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=required).copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["target_class"] = potential_to_class(df["target_potencial_cliente"])
    df = df.sort_values(
        ["__dataset_source__", "Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"],
        kind="mergesort",
    ).reset_index(drop=True)

    samples = build_sequence_samples(
        df,
        max_seq_len=int(checkpoint["max_seq_len"]),
        min_history=int(checkpoint["min_history"]),
    )
    if not samples:
        raise ValueError("No sequence samples were created for evaluation.")

    feature_frame, _ = build_feature_frame(df)
    feature_names = list(checkpoint["feature_names"])
    feature_means = _checkpoint_mapping(checkpoint["feature_means"])
    feature_stds = _checkpoint_mapping(checkpoint["feature_stds"])
    features = align_and_normalize_features(feature_frame, feature_names, feature_means, feature_stds)

    device = torch.device(
        "cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu" if args.device == "auto" else args.device
    )
    model = SequentialPotentialModel(
        input_size=int(checkpoint["input_size"]),
        hidden_size=int(checkpoint["hidden_size"]),
        num_layers=int(checkpoint["num_layers"]),
        dropout=float(checkpoint["dropout"]),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])

    loader = DataLoader(
        PotentialSequenceDataset(features, samples),
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_sequences,
    )

    print(
        "Evaluating full dataset: "
        f"rows={len(df):,}, sequence_samples={len(samples):,}, features={features.shape[1]:,}, "
        f"model={model_path}"
    )
    metrics, confusion = evaluate_full_dataset(model, loader, device)

    print("\n=== Full dataset metrics ===")
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")
    print_confusion(confusion)


if __name__ == "__main__":
    main()
