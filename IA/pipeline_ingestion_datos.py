from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from generar_dataset_previo_potencial_nuevo import recalcular_potencial


HORIZONTE_FIDELIZACION_DIAS = 365
DEFAULT_NO_RECOMPRA_DIAS = 1500

OUTPUT_COLUMNS = [
    "Num.Fact",
    "Fecha",
    "Id. Cliente",
    "Id. Producto",
    "Unidades",
    "Valores_H",
    "Bloque analítico",
    "Categoria_H",
    "Familia_H",
    "tiempo_medio_recompra_dias",
    "std_recompra_dias",
    "dias_desde_compra_anterior_producto",
    "tiempo_medio_entre_compras_dias",
    "std_entre_compras_dias",
    "zscore_momento_cliente_producto",
    "zscore_momento_recompra_general",
    "n_anios_cliente_categoria",
    "gasto_medio_anual_cliente_categoria_producto",
    "gasto_medio_anual_cliente_categoria",
    "peso_producto_en_categoria",
    "gasto_anual_real_cliente_producto",
    "numero_compras_anteriores_producto",
    "total_compras_cliente_otros_productos",
    "numero_devoluciones_producto",
    "vuelve_a_comprar",
    "dias_hasta_proxima_compra",
    "target_potencial_cliente",
    "gasto_base_anual_fidelizacion",
    "gasto_futuro_anual_fidelizacion",
    "frecuencia_base_anual_fidelizacion",
    "frecuencia_futura_anual_fidelizacion",
]


def load_excel(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    productos = pd.read_excel(path, sheet_name="Productos")
    ventas = pd.read_excel(path, sheet_name="Ventas")
    clientes = pd.read_excel(path, sheet_name="Clientes")
    clientes = clientes.drop(columns=[col for col in ["Unnamed: 1", "Provincia"] if col in clientes.columns])
    return ventas, productos, clientes


def add_product_repurchase_stats(ventas: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    ventas_validas = ventas[(ventas["Unidades"] > 0) & (ventas["Valores_H"] > 0)].copy()
    ventas_validas["Fecha"] = pd.to_datetime(ventas_validas["Fecha"])
    ventas_validas = ventas_validas.sort_values(["Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"])
    ventas_validas["dias_entre_compras"] = (
        ventas_validas.groupby(["Id. Cliente", "Id. Producto"])["Fecha"].diff().dt.days
    )
    stats_producto = (
        ventas_validas.dropna(subset=["dias_entre_compras"])
        .groupby("Id. Producto")["dias_entre_compras"]
        .agg(tiempo_medio_recompra_dias="mean", std_recompra_dias="std")
        .reset_index()
    )
    return productos.merge(stats_producto, left_on="Id.Prod", right_on="Id. Producto", how="left").drop(
        columns=["Id. Producto"]
    )


def build_client_product_metrics(ventas: pd.DataFrame) -> pd.DataFrame:
    compras = ventas[(ventas["Unidades"] > 0) & (ventas["Valores_H"] > 0)].copy()
    compras["Fecha"] = pd.to_datetime(compras["Fecha"])
    compras = compras.sort_values(["Id. Cliente", "Id. Producto", "Fecha", "Num.Fact"])
    compras["dias_entre_compras"] = compras.groupby(["Id. Cliente", "Id. Producto"])["Fecha"].diff().dt.days

    metricas = (
        compras.groupby(["Id. Cliente", "Id. Producto"], as_index=False)
        .agg(
            tiempo_medio_entre_compras_dias=("dias_entre_compras", "mean"),
            std_entre_compras_dias=("dias_entre_compras", "std"),
        )
        .reset_index(drop=True)
    )
    return metricas


def enrich_sales(ventas: pd.DataFrame, productos: pd.DataFrame, metricas_cliente_producto: pd.DataFrame) -> pd.DataFrame:
    ventas_enriquecidas = ventas.copy()
    ventas_enriquecidas["_orden_original"] = range(len(ventas_enriquecidas))
    ventas_enriquecidas["Fecha"] = pd.to_datetime(ventas_enriquecidas["Fecha"])

    producto_cols = [
        "Id.Prod",
        "Bloque analítico",
        "Categoria_H",
        "Familia_H",
        "tiempo_medio_recompra_dias",
        "std_recompra_dias",
    ]
    ventas_enriquecidas = ventas_enriquecidas.merge(
        productos[producto_cols],
        left_on="Id. Producto",
        right_on="Id.Prod",
        how="left",
    ).drop(columns=["Id.Prod"])

    ventas_enriquecidas = ventas_enriquecidas.sort_values(
        ["Id. Cliente", "Id. Producto", "Fecha", "Num.Fact", "_orden_original"]
    ).copy()
    ventas_enriquecidas["_es_compra_valida"] = (
        (ventas_enriquecidas["Unidades"] > 0) & (ventas_enriquecidas["Valores_H"] > 0)
    )
    ventas_enriquecidas["_fecha_compra_valida"] = ventas_enriquecidas["Fecha"].where(
        ventas_enriquecidas["_es_compra_valida"]
    )
    ventas_enriquecidas["_compra_valida_int"] = ventas_enriquecidas["_es_compra_valida"].astype(int)
    ventas_enriquecidas["numero_compras_anteriores_producto"] = (
        ventas_enriquecidas.groupby(["Id. Cliente", "Id. Producto"])["_compra_valida_int"].cumsum()
        - ventas_enriquecidas["_compra_valida_int"]
    )

    compras_cliente_producto = ventas_enriquecidas.groupby(["Id. Cliente", "Id. Producto"])[
        "_compra_valida_int"
    ].transform("sum")
    compras_cliente = ventas_enriquecidas.groupby("Id. Cliente")["_compra_valida_int"].transform("sum")
    ventas_enriquecidas["total_compras_cliente_otros_productos"] = compras_cliente - compras_cliente_producto

    ventas_enriquecidas["_es_devolucion_int"] = (ventas_enriquecidas["Valores_H"] <= 0).astype(int)
    ventas_enriquecidas["numero_devoluciones_producto"] = ventas_enriquecidas.groupby(
        ["Id. Cliente", "Id. Producto"]
    )["_es_devolucion_int"].transform("sum")
    ventas_enriquecidas["fecha_compra_anterior_producto"] = ventas_enriquecidas.groupby(
        ["Id. Cliente", "Id. Producto"]
    )["_fecha_compra_valida"].transform(lambda s: s.shift().ffill())
    ventas_enriquecidas["dias_desde_compra_anterior_producto"] = (
        ventas_enriquecidas["Fecha"] - ventas_enriquecidas["fecha_compra_anterior_producto"]
    ).dt.days

    ventas_enriquecidas = ventas_enriquecidas.merge(
        metricas_cliente_producto,
        on=["Id. Cliente", "Id. Producto"],
        how="left",
    )

    std_cliente_producto = ventas_enriquecidas["std_entre_compras_dias"].mask(
        ventas_enriquecidas["std_entre_compras_dias"] == 0
    )
    ventas_enriquecidas["zscore_momento_cliente_producto"] = (
        ventas_enriquecidas["dias_desde_compra_anterior_producto"]
        - ventas_enriquecidas["tiempo_medio_entre_compras_dias"]
    ) / std_cliente_producto

    std_recompra_general = ventas_enriquecidas["std_recompra_dias"].mask(
        ventas_enriquecidas["std_recompra_dias"] == 0
    )
    ventas_enriquecidas["zscore_momento_recompra_general"] = (
        ventas_enriquecidas["dias_desde_compra_anterior_producto"]
        - ventas_enriquecidas["tiempo_medio_recompra_dias"]
    ) / std_recompra_general

    ventas_enriquecidas = add_category_spend_features(ventas_enriquecidas)
    return ventas_enriquecidas


def add_category_spend_features(df: pd.DataFrame) -> pd.DataFrame:
    ventas_validas = df[df["_es_compra_valida"]].copy()
    ventas_validas["anio"] = ventas_validas["Fecha"].dt.year

    anios_cliente_categoria = (
        ventas_validas.groupby(["Id. Cliente", "Categoria_H"], as_index=False)
        .agg(n_anios_cliente_categoria=("anio", "nunique"))
    )

    gasto_producto_categoria = (
        ventas_validas.groupby(["Id. Cliente", "Categoria_H", "Id. Producto"], as_index=False)
        .agg(gasto_total_cliente_categoria_producto=("Valores_H", "sum"))
        .merge(anios_cliente_categoria, on=["Id. Cliente", "Categoria_H"], how="left")
    )
    gasto_producto_categoria["gasto_medio_anual_cliente_categoria_producto"] = (
        gasto_producto_categoria["gasto_total_cliente_categoria_producto"]
        / gasto_producto_categoria["n_anios_cliente_categoria"].mask(
            gasto_producto_categoria["n_anios_cliente_categoria"] == 0
        )
    )

    gasto_cliente_categoria = (
        ventas_validas.groupby(["Id. Cliente", "Categoria_H"], as_index=False)
        .agg(gasto_total_cliente_categoria=("Valores_H", "sum"))
        .merge(anios_cliente_categoria, on=["Id. Cliente", "Categoria_H"], how="left")
    )
    gasto_cliente_categoria["gasto_medio_anual_cliente_categoria"] = (
        gasto_cliente_categoria["gasto_total_cliente_categoria"]
        / gasto_cliente_categoria["n_anios_cliente_categoria"].mask(
            gasto_cliente_categoria["n_anios_cliente_categoria"] == 0
        )
    )

    gasto_producto_categoria = gasto_producto_categoria.merge(
        gasto_cliente_categoria[
            ["Id. Cliente", "Categoria_H", "gasto_total_cliente_categoria", "gasto_medio_anual_cliente_categoria"]
        ],
        on=["Id. Cliente", "Categoria_H"],
        how="left",
    )
    gasto_producto_categoria["peso_producto_en_categoria"] = (
        gasto_producto_categoria["gasto_medio_anual_cliente_categoria_producto"]
        / gasto_producto_categoria["gasto_medio_anual_cliente_categoria"].mask(
            gasto_producto_categoria["gasto_medio_anual_cliente_categoria"] == 0
        )
    )

    gasto_anual_producto = (
        ventas_validas.groupby(["Id. Cliente", "Id. Producto", "anio"], as_index=False)
        .agg(gasto_anual_real_cliente_producto=("Valores_H", "sum"))
    )
    df = df.copy()
    df["anio"] = df["Fecha"].dt.year
    df = df.merge(
        gasto_producto_categoria[
            [
                "Id. Cliente",
                "Categoria_H",
                "Id. Producto",
                "n_anios_cliente_categoria",
                "gasto_medio_anual_cliente_categoria_producto",
                "gasto_medio_anual_cliente_categoria",
                "peso_producto_en_categoria",
            ]
        ],
        on=["Id. Cliente", "Categoria_H", "Id. Producto"],
        how="left",
    )
    df = df.merge(
        gasto_anual_producto,
        on=["Id. Cliente", "Id. Producto", "anio"],
        how="left",
    )
    return df.drop(columns=["anio"])


def add_future_targets(df: pd.DataFrame) -> pd.DataFrame:
    compras = df[df["_es_compra_valida"]].copy()
    compras = compras.sort_values(["Id. Cliente", "Id. Producto", "Fecha", "Num.Fact", "_orden_original"]).copy()
    compras["fecha_proxima_compra_producto"] = compras.groupby(["Id. Cliente", "Id. Producto"])["Fecha"].shift(-1)
    compras["vuelve_a_comprar"] = compras["fecha_proxima_compra_producto"].notna().astype(int)
    compras["dias_hasta_proxima_compra"] = (
        compras["fecha_proxima_compra_producto"] - compras["Fecha"]
    ).dt.days.fillna(DEFAULT_NO_RECOMPRA_DIAS).clip(lower=0).astype(int)
    return compras


def add_fidelization_audit_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    gasto_base_all = np.zeros(len(df), dtype=float)
    gasto_futuro_all = np.zeros(len(df), dtype=float)
    freq_base_all = np.zeros(len(df), dtype=float)
    freq_futura_all = np.zeros(len(df), dtype=float)

    for _, group in df.groupby(["Id. Cliente", "Id. Producto"], sort=False, dropna=False):
        group = group.sort_values(["Fecha", "Num.Fact", "_orden_original"])
        idx = group.index.to_numpy()
        fechas = group["Fecha"].astype("int64").to_numpy() // 86_400_000_000_000
        valores = group["Valores_H"].to_numpy(dtype=float)
        cumsum = np.concatenate([[0.0], np.cumsum(valores)])
        posiciones = np.arange(len(group))

        inicio_base = np.searchsorted(fechas, fechas - HORIZONTE_FIDELIZACION_DIAS, side="left")
        fin_futuro = np.searchsorted(fechas, fechas + HORIZONTE_FIDELIZACION_DIAS, side="right")

        gasto_base_all[idx] = cumsum[posiciones + 1] - cumsum[inicio_base]
        gasto_futuro_all[idx] = cumsum[fin_futuro] - cumsum[posiciones + 1]
        freq_base_all[idx] = posiciones - inicio_base + 1
        freq_futura_all[idx] = fin_futuro - posiciones - 1

    df["gasto_base_anual_fidelizacion"] = gasto_base_all
    df["gasto_futuro_anual_fidelizacion"] = gasto_futuro_all
    df["frecuencia_base_anual_fidelizacion"] = freq_base_all
    df["frecuencia_futura_anual_fidelizacion"] = freq_futura_all
    return df


def build_dataset(input_path: Path) -> pd.DataFrame:
    ventas, productos, _clientes = load_excel(input_path)
    productos = add_product_repurchase_stats(ventas, productos)
    metricas_cliente_producto = build_client_product_metrics(ventas)
    ventas_enriquecidas = enrich_sales(ventas, productos, metricas_cliente_producto)
    dataset = add_future_targets(ventas_enriquecidas)
    dataset = add_fidelization_audit_columns(dataset)
    dataset["target_potencial_cliente"] = recalcular_potencial(dataset)

    dataset = dataset.sort_values("_orden_original").copy()
    for col in OUTPUT_COLUMNS:
        if col not in dataset.columns:
            dataset[col] = np.nan

    dataset = dataset[OUTPUT_COLUMNS].copy()
    numeric_cols = dataset.select_dtypes(include=[np.number]).columns
    dataset[numeric_cols] = dataset[numeric_cols].replace([np.inf, -np.inf], np.nan)
    dataset["dias_desde_compra_anterior_producto"] = dataset[
        "dias_desde_compra_anterior_producto"
    ].fillna(-1)
    dataset[numeric_cols] = dataset[numeric_cols].fillna(0)
    return dataset.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dataset_v2-like CSV from Datasets.xlsx")
    parser.add_argument("--input", type=Path, default=Path("Datasets.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("dataset_v2_generado.csv"))
    args = parser.parse_args()

    dataset = build_dataset(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False, encoding="utf-8-sig")

    print(f"CSV generado: {args.output}")
    print(f"Filas: {len(dataset):,} Columnas: {len(dataset.columns):,}")
    print("\ntarget_potencial_cliente:")
    print(dataset["target_potencial_cliente"].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    print("\nvuelve_a_comprar:")
    print(dataset["vuelve_a_comprar"].value_counts(dropna=False).sort_index())


if __name__ == "__main__":
    main()
