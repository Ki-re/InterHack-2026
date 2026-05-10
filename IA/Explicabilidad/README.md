# IA

Esta carpeta contiene los modelos de inferencia para scoring comercial sobre cliente-producto.
El reporte se genera con `model_feature_importance.py` a partir de los modelos guardados y calcula explicabilidad por importancia de permutacion.

## Como regenerar el reporte

```powershell
conda run -n interhack python IA/Explicabilidad/model_feature_importance.py --dataset IA/dataset.csv --write-readme
```

La importancia mide cuanto empeora la metrica del modelo al desordenar una variable. Valores mayores indican que el modelo depende mas de esa variable.
Dataset analizado: `IA/dataset.csv`. Filas muestreadas por modelo: `5000`.

## Modelos

### fuga_model.pt

- Objetivo: Estimar la probabilidad de que el cliente no vuelva a comprar a partir del modelo binario de recompra.
- Arquitectura: Red neuronal feed-forward con capas densas, BatchNorm, activacion SiLU y dropout; salida logit binaria.
- Metrica de importancia: `incremento_bce`.
- Muestra evaluada: 5,000 ejemplos.
- Baseline: bce=0.1198, accuracy=0.9672.

| Variable | Importancia | Max. feature | Features codificadas |
|---|---:|---:|---:|
| tiempo_medio_entre_compras_dias | 3.538898 | 3.538898 | 1 |
| numero_compras_anteriores_producto | 2.987885 | 2.987885 | 1 |
| gasto_medio_anual_cliente_categoria_producto | 1.483805 | 1.483805 | 1 |
| gasto_anual_real_cliente_producto | 0.906181 | 0.906181 | 1 |
| Valores_H | 0.677819 | 0.677819 | 1 |
| n_anios_cliente_categoria | 0.513312 | 0.513312 | 1 |
| Familia_H | 0.403416 | 0.209942 | 5 |
| Categoria_H | 0.341404 | 0.126700 | 4 |
| std_entre_compras_dias | 0.163558 | 0.163558 | 1 |
| Bloque analítico | 0.146796 | 0.089887 | 3 |
| dias_desde_compra_anterior_producto | 0.128799 | 0.128799 | 1 |
| zscore_momento_recompra_general | 0.113113 | 0.113113 | 1 |

### potencial_model.pt

- Objetivo: Clasificar el potencial futuro del cliente-producto en cinco clases ordenadas y convertirlo en score 0-100.
- Arquitectura: Modelo secuencial GRU que resume el historial cliente-producto y aplica una cabeza densa multiclase.
- Metrica de importancia: `incremento_cross_entropy`.
- Muestra evaluada: 5,000 ejemplos.
- Baseline: cross_entropy=3.6690, accuracy=0.2184.

| Variable | Importancia | Max. feature | Features codificadas |
|---|---:|---:|---:|
| Categoria_H | 3.312089 | 3.082363 | 4 |
| Familia_H | 1.154469 | 0.765885 | 5 |
| Bloque analítico | 0.320041 | 0.264115 | 3 |
| zscore_momento_cliente_producto | 0.273815 | 0.273815 | 1 |
| n_anios_cliente_categoria | 0.128392 | 0.128392 | 1 |
| peso_producto_en_categoria | 0.126509 | 0.126509 | 1 |
| numero_compras_anteriores_producto | 0.045029 | 0.045029 | 1 |
| zscore_momento_recompra_general | 0.025114 | 0.025114 | 1 |
| Unidades | 0.024332 | 0.024332 | 1 |
| numero_devoluciones_producto | 0.018476 | 0.018476 | 1 |
| dias_desde_compra_anterior_producto | 0.016551 | 0.016551 | 1 |
| std_entre_compras_dias | 0.009479 | 0.009479 | 1 |

### dias_model.pt

- Objetivo: Predecir los dias hasta la proxima compra y una clase auxiliar de mes de recompra.
- Arquitectura: Modelo secuencial GRU con una representacion compartida y dos cabezas: regresion de dias en escala log y clasificacion auxiliar.
- Metrica de importancia: `incremento_loss`.
- Muestra evaluada: 5,000 ejemplos.
- Baseline: loss=4.9524, mae_days=132.2270.

| Variable | Importancia | Max. feature | Features codificadas |
|---|---:|---:|---:|
| ratio_recompra_vs_cliente | 0.205142 | 0.205142 | 1 |
| Familia_H | 0.096067 | 0.083349 | 5 |
| Categoria_H | 0.075067 | 0.075067 | 4 |
| ratio_recencia_vs_producto | 0.056511 | 0.056511 | 1 |
| dias_desde_compra_anterior_producto | 0.055188 | 0.055188 | 1 |
| fecha_dia_anio_cos | 0.054963 | 0.054963 | 1 |
| Bloque analítico | 0.031982 | 0.031982 | 3 |
| peso_producto_en_categoria | 0.021464 | 0.021464 | 1 |
| n_anios_cliente_categoria | 0.014826 | 0.014826 | 1 |
| std_entre_compras_dias | 0.012393 | 0.012393 | 1 |
| tiempo_medio_entre_compras_dias | 0.005526 | 0.005526 | 1 |
| Unidades | 0.002768 | 0.002768 | 1 |

## Notas de interpretacion

- La explicabilidad es global sobre la muestra usada, no una explicacion individual por prediccion.
- Las variables categoricas se agregan desde sus columnas one-hot para que el ranking sea legible por variable original.
- Las columnas objetivo, identificadores y variables de fuga temporal se excluyen de las entradas del modelo.
