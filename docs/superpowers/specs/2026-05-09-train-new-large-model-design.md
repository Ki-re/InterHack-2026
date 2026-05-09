# Diseno: `IA/train_new.py` para modelo tabular grande

## Objetivo

Crear una nueva version de entrenamiento en `IA/train_new.py` que mantenga intacto `IA/train.py` y use el dataset `IA/dataset_modelo.csv` para entrenar un modelo tabular mayor, pensado para ejecuciones largas en GPU con checkpoints.

## Contexto

El script actual `IA/train.py` entrena un MLP pequeno de una capa oculta de 32 unidades y guarda un unico `purchase_model.pt` al final. El CSV contiene 156.921 filas, 31 columnas, 3 targets y una mezcla de variables numericas y categoricas. La salida actual ya restringe correctamente cada target:

- `vuelve_a_comprar`: probabilidad entre 0 y 1.
- `dias_hasta_proxima_compra`: valor positivo.
- `target_potencial_cliente`: valor entre -1 y 1.

## Enfoque elegido

Implementar un MLP tabular grande configurable, con valores por defecto para entrenamiento largo:

- Capas ocultas por defecto: `512,256,128,64`.
- Activacion `SiLU`.
- `BatchNorm1d` despues de cada capa lineal.
- `Dropout` configurable, por defecto moderado.
- Optimizador `AdamW`.
- `ReduceLROnPlateau` sobre `val_loss`.
- Clipping de gradiente para estabilizar entrenamientos largos.

Este enfoque mejora la capacidad del modelo sin cambiar la semantica de los datos ni introducir un pipeline de embeddings mas complejo.

## Flujo de datos

`train_new.py` reutilizara la misma idea de preprocessing del script actual:

- Leer CSV desde `--csv`.
- Eliminar filas sin targets.
- Dividir train/validation/test con seed reproducible.
- Excluir targets, identificadores y columnas de leakage.
- One-hot encoding de categoricas.
- Reemplazar infinitos y nulos por cero.
- Estandarizar features usando solo train.
- Construir tensores para PyTorch.

## Checkpoints

El nuevo script guardara checkpoints en `--checkpoint-dir`, por defecto `IA/checkpoints_large`.

Cada checkpoint incluira:

- Epoca.
- Estado del modelo.
- Estado del optimizador.
- Estado del scheduler.
- Metricas de train y validation.
- Nombres de features.
- Columnas target.
- Configuracion usada.

Tambien guardara `best_model.pt` cuando mejore `val_loss` y `last_model.pt` al final.

## CLI

Argumentos principales:

- `--epochs`: numero de epocas.
- `--batch-size`: tamano de batch.
- `--lr`: learning rate.
- `--weight-decay`: regularizacion AdamW.
- `--hidden-sizes`: lista separada por comas.
- `--dropout`: dropout.
- `--checkpoint-dir`: carpeta de salida.
- `--checkpoint-every`: frecuencia de checkpoints periodicos.
- `--num-workers`: workers del DataLoader.
- `--grad-clip`: norma maxima de gradiente.

## Validacion

La implementacion se validara con:

- Compilacion sintactica de `IA/train_new.py`.
- Ejecucion corta de humo con pocas epocas si el entorno tiene dependencias disponibles.
- Comando final recomendado para entrenamiento largo con checkpoints.

## Fuera de alcance

- No modificar `IA/train.py`.
- No reescribir el notebook `IA/Datos.ipynb`.
- No introducir embeddings categoricos ni modelos de gradient boosting en esta iteracion.
- No cambiar el dataset.
