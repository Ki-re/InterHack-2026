@echo off

REM Crear entorno
conda create -n interhack python=3.10 -y

REM Activar entorno
call conda activate interhack

REM Instalar paquetes
pip install numpy pandas polars scipy scikit-learn xgboost lightgbm catboost matplotlib seaborn plotly tqdm rich jupyterlab notebook ipykernel statsmodels sympy duckdb pyarrow openpyxl xlrd requests beautifulsoup4 lxml opencv-python pillow transformers datasets accelerate evaluate wandb

echo.
echo =====================================
echo Entorno "interhack" listo
echo =====================================

pause