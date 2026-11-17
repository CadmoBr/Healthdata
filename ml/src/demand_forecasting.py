"""
Módulo de Previsão de Demanda Hospitalar (SIH/SUS)
Utiliza o histórico expandido (2019-2026) da camada Gold (Star Schema) para 
engenharia de features temporais, treinamento e avaliação do RandomForestRegressor.
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from src.utils.logger import get_logger

load_dotenv(override=True)
logger = get_logger("demand_forecasting")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/healthdata")
REPORTS_PATH = Path("docs")


def get_db_engine():
    return create_engine(DATABASE_URL)


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
    df = pd.read_sql(query, con=engine)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria features de defasagem (lags), médias móveis e codificação sazonal trigonométrica."""
    df = df.copy()
    
    # Garante ordenação temporal correta
    df = df.sort_values(by="competencia").reset_index(drop=True)
    
    # Target (produção hospitalar)
    target_col = "total_producao"
    
    # Lags temporais (ex: 1, 2, 3 e 12 meses anteriores para sazonalidade anual)
    for lag in [1, 2, 3, 12]:
        df[f"lag_{lag}"] = df[target_col].shift(lag)
        
    # Médias móveis (janelas de 3 e 6 meses)
    df["rolling_mean_3"] = df[target_col].shift(1).rolling(window=3).mean()
    df["rolling_mean_6"] = df[target_col].shift(1).rolling(window=6).mean()
    
    # Codificação sazonal trigonométrica (Seno/Cosseno para o mês)
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    
    # Remove linhas com valores nulos gerados pelos lags/médias móveis iniciais
    df = df.dropna().reset_index(drop=True)
    return df


def train_and_evaluate_model():
    df_raw = load_gold_data()
    if df_raw.empty or len(df_raw) < 15:
        logger.error("Dados insuficientes na camada Gold para treinar o modelo de forecasting.")
        return

    df_featured = engineer_features(df_raw)
    
    feature_cols = [
        "ano", "mes", 
        "lag_1", "lag_2", "lag_3", "lag_12", 
        "rolling_mean_3", "rolling_mean_6",
        "mes_sin", "mes_cos"
    ]
    target_col = "total_producao"

    X = df_featured[feature_cols]
    y = df_featured[target_col]

    # Validação temporal rigorosa (TimeSeriesSplit)
    tscv = TimeSeriesSplit(n_splits=5)
    
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

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

    # Treinamento final com todo o dataset histórico expandido
    model.fit(X, y)
    logger.info("Modelo RandomForest treinado com sucesso em todo o histórico de 2019 a 2026.")

    # Salvando relatório de avaliação em docs/ml_evaluation_report.md
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_content = f"""# Relatório de Avaliação de Machine Learning - HealthData Intelligence
**Período de Dados:** 2019 a 2026 (Histórico Expandido)
**Modelo Utilizado:** RandomForestRegressor
**Estratégia de Validação:** TimeSeriesSplit (5 splits)

## Métricasmédias de Validação Cruzada Temporal:
- **MAE Médio:** {np.mean(maes):,.2f}
- **RMSE Médio:** {np.mean(rmses):,.2f}
- **R² Médio:** {np.mean(r2s):.4f}
"""
    report_file = REPORTS_PATH / "ml_evaluation_report.md"
    report_file.write_text(report_content, encoding="utf-8")
    logger.info(f"Relatório de ML salvo em '{report_file}'.")


if __name__ == "__main__":
    train_and_evaluate_model()