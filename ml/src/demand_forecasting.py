"""
Módulo de Previsão de Demanda Hospitalar (SIH/SUS)
Utiliza o histórico expandido (2019-2026) da camada Gold (Star Schema) para 
engenharia de features temporais, treinamento e avaliação de modelos.
"""

import os
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from src.utils.logger import get_logger

load_dotenv(override=True)
logger = get_logger("demand_forecasting")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/healthdata")
REPORTS_PATH = Path("docs")


def get_db_engine():
    return create_engine(DATABASE_URL)


def explore_trend_seasonality_and_impute(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Ordena a série temporal, trata eventuais valores ausentes sem vazamento de dados e retorna sumário."""
    df = raw_df.copy().sort_values("competencia").reset_index(drop=True)
    target_col = "volume_internacoes" if "volume_internacoes" in df.columns else "total_producao"

    missing_before = int(df[target_col].isna().sum()) if target_col in df.columns else 0
    if target_col in df.columns:
        df[target_col] = pd.to_numeric(df[target_col], errors="coerce").ffill().bfill()

    stats = {
        "periods": len(df),
        "missing_imputed": missing_before,
        "mean_volume": float(df[target_col].mean()) if target_col in df.columns and len(df) > 0 else 0.0,
    }
    return df, stats


def build_time_series_features(series_df: pd.DataFrame) -> pd.DataFrame:
    """Gera features de defasagem (lags 1 a 3), médias móveis estritamente passadas e codificação cíclica."""
    df = series_df.copy().sort_values("competencia").reset_index(drop=True)
    target_col = "volume_internacoes" if "volume_internacoes" in df.columns else "total_producao"

    if "mes" not in df.columns:
        df["mes"] = pd.to_numeric(df["competencia"].astype(str).str.slice(4, 6), errors="coerce").fillna(1).astype(int)
    if "ano" not in df.columns:
        df["ano"] = pd.to_numeric(df["competencia"].astype(str).str.slice(0, 4), errors="coerce").fillna(2025).astype(int)
    if "trimestre" not in df.columns:
        df["trimestre"] = ((df["mes"] - 1) // 3) + 1

    df["trend_idx"] = np.arange(len(df), dtype=float)
    df["lag_1"] = df[target_col].shift(1)
    df["lag_2"] = df[target_col].shift(2)
    df["lag_3"] = df[target_col].shift(3)

    df["rolling_mean_3"] = df[target_col].shift(1).rolling(window=3, min_periods=3).mean()
    df["rolling_std_3"] = df[target_col].shift(1).rolling(window=3, min_periods=3).std().fillna(0.0)

    df["month_sin"] = np.sin(2 * np.pi * df["mes"] / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * df["mes"] / 12.0)

    df = df.dropna(subset=["lag_1", "lag_2", "lag_3", "rolling_mean_3"]).reset_index(drop=True)
    return df


def train_and_evaluate_models(
    features_df: pd.DataFrame,
    test_horizon: int = 4,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Treina e avalia modelos em janela Out-of-Time comparando contra o Baseline Naive Lag-1."""
    df = features_df.copy().reset_index(drop=True)
    target_col = "volume_internacoes" if "volume_internacoes" in df.columns else "total_producao"

    feature_cols = [
        c
        for c in [
            "trend_idx",
            "mes",
            "trimestre",
            "lag_1",
            "lag_2",
            "lag_3",
            "rolling_mean_3",
            "rolling_std_3",
            "month_sin",
            "month_cos",
        ]
        if c in df.columns
    ]

    split_idx = max(len(df) - test_horizon, 1)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]

    try:
        from xgboost import XGBRegressor

        xgb_model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=42, verbosity=0)
    except Exception:
        xgb_model = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=42)

    models = {
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(n_estimators=150, max_depth=6, random_state=42),
        "XGBRegressor": xgb_model,
    }

    preds_dict: Dict[str, np.ndarray] = {
        "Naive_Lag1_Baseline": test_df["lag_1"].to_numpy(dtype=float),
    }

    for name, mdl in models.items():
        mdl.fit(X_train, y_train)
        preds_dict[name] = mdl.predict(X_test)

    metrics_rows = []
    y_true = y_test.to_numpy(dtype=float)

    for model_name, y_pred in preds_dict.items():
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-6))) * 100.0)
        metrics_rows.append(
            {
                "model_name": model_name,
                "MAE": mae,
                "RMSE": rmse,
                "MAPE_pct": mape,
            }
        )

    metrics_df = pd.DataFrame(metrics_rows).sort_values("MAE").reset_index(drop=True)

    predictions_df = test_df[["competencia"]].copy()
    predictions_df["y_true"] = y_true
    for model_name, y_pred in preds_dict.items():
        predictions_df[model_name] = y_pred

    metadata = {
        "train_periods": len(train_df),
        "test_periods": len(test_df),
        "champion_model": str(metrics_df.iloc[0]["model_name"]),
    }

    return metrics_df, predictions_df, metadata


def load_gold_data() -> pd.DataFrame:
    """Carrega os dados consolidados da tabela fato na camada Gold."""
    engine = get_db_engine()
    query = """
        SELECT
            d.sk_date AS competencia,
            d.ano,
            d.mes,
            SUM(p.qt_procedimento) AS total_producao,
            SUM(p.vl_procedimento) AS total_valor
        FROM dw_gold.fact_hospital_production AS p
        INNER JOIN dw_gold.dim_date AS d
            ON p.fk_date = d.sk_date
        GROUP BY d.sk_date, d.ano, d.mes
        ORDER BY d.sk_date ASC;
    """
    logger.info("Carregando dados históricos da camada Gold para forecasting...")
    return pd.read_sql(query, con=engine)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria features de defasagem (lags), médias móveis e codificação sazonal trigonométrica."""
    df = df.copy().sort_values(by="competencia").reset_index(drop=True)
    target_col = "total_producao"

    for lag in [1, 2, 3, 12]:
        df[f"lag_{lag}"] = df[target_col].shift(lag)

    df["rolling_mean_3"] = df[target_col].shift(1).rolling(window=3).mean()
    df["rolling_mean_6"] = df[target_col].shift(1).rolling(window=6).mean()

    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    return df.dropna().reset_index(drop=True)


def train_and_evaluate_model():
    df_raw = load_gold_data()
    if df_raw.empty or len(df_raw) < 15:
        logger.error("Dados insuficientes na camada Gold para treinar o modelo de forecasting.")
        return

    df_featured = engineer_features(df_raw)

    feature_cols = [
        "ano",
        "mes",
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_12",
        "rolling_mean_3",
        "rolling_mean_6",
        "mes_sin",
        "mes_cos",
    ]
    target_col = "total_producao"

    X = df_featured[feature_cols]
    y = df_featured[target_col]

    tscv = TimeSeriesSplit(n_splits=5)
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

    maes, rmses, r2s = [], [], []

    logger.info("Iniciando treinamento e validação com TimeSeriesSplit (2019-2026)...")
    for fold, (train_index, test_index) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        maes.append(mae)
        rmses.append(rmse)
        r2s.append(r2)
        logger.info(f"Fold {fold+1} | MAE: {mae:.2f} | RMSE: {rmse:.2f} | R2: {r2:.4f}")

    model.fit(X, y)
    logger.info("Modelo RandomForest treinado com sucesso em todo o histórico de 2019 a 2026.")

    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_content = f"""# Relatório de Avaliação de Machine Learning - HealthData Intelligence
**Período de Dados:** 2019 a 2026 (Histórico Expandido)
**Modelo Utilizado:** RandomForestRegressor
**Estratégia de Validação:** TimeSeriesSplit (5 splits)

## Métricas Médias de Validação Cruzada Temporal:
- **MAE Médio:** {np.mean(maes):,.2f}
- **RMSE Médio:** {np.mean(rmses):,.2f}
- **R² Médio:** {np.mean(r2s):.4f}
"""
    report_file = REPORTS_PATH / "ml_evaluation_report.md"
    report_file.write_text(report_content, encoding="utf-8")
    logger.info(f"Relatório de ML salvo em '{report_file}'.")


if __name__ == "__main__":
    train_and_evaluate_model()