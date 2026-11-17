"""
Previsão experimental de demanda hospitalar a partir da camada Gold do SIH/SUS.

O módulo agrega a série mensal, cria atributos temporais sem usar valores futuros,
compara modelos de regressão com um baseline e gera artefatos de avaliação.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from xgboost import XGBRegressor

from src.utils.db import get_db_engine
from src.utils.logger import get_logger

logger = get_logger("ml_demand_forecasting")

FEATURE_COLUMNS = [
    "trend_idx",
    "month_sin",
    "month_cos",
    "lag_1",
    "lag_2",
    "lag_3",
    "rolling_mean_3",
    "rolling_std_3",
]


def load_monthly_series_from_gold() -> pd.DataFrame:
    """Carrega a série mensal agregada diretamente do PostgreSQL (DW Gold)."""
    engine = get_db_engine()
    sql = text(
        """
        SELECT
            d.sk_date AS competencia,
            d.reference_date AS ds_data,
            d.ano,
            d.mes,
            d.trimestre,
            SUM(p.qt_procedimento)::DOUBLE PRECISION AS volume_internacoes,
            SUM(p.vl_procedimento)::DOUBLE PRECISION AS valor_aprovado
        FROM dw_gold.fact_hospital_production AS p
        INNER JOIN dw_gold.dim_date AS d
            ON p.fk_date = d.sk_date
        GROUP BY
            d.sk_date, d.reference_date, d.ano, d.mes, d.trimestre
        ORDER BY d.reference_date ASC
        """
    )

    try:
        with engine.connect() as connection:
            df = pd.read_sql(sql, connection)
    finally:
        engine.dispose()

    if df.empty:
        raise RuntimeError(
            "A tabela dw_gold.fact_hospital_production não possui dados. "
            "Execute primeiro as etapas de ingestão e transformação."
        )

    required = {"ds_data", "volume_internacoes", "valor_aprovado"}
    missing_columns = required.difference(df.columns)
    if missing_columns:
        raise ValueError(
            f"Colunas obrigatórias ausentes na consulta Gold: {sorted(missing_columns)}"
        )

    df["ds_data"] = pd.to_datetime(df["ds_data"], errors="coerce")
    df = df.dropna(subset=["ds_data"]).sort_values("ds_data").reset_index(drop=True)

    if df.empty:
        raise ValueError("Nenhuma data válida foi retornada pela camada Gold.")

    logger.info(
        "[ETAPA 1 - EDA] %s competências carregadas (%s a %s).",
        len(df),
        df["ds_data"].min().date(),
        df["ds_data"].max().date(),
    )
    return df


def explore_trend_seasonality_and_impute(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Garante calendário mensal contínuo e preenche lacunas somente com o último
    valor observado. Lacunas no início da série não são preenchidas com dados futuros.
    """
    if df.empty:
        raise ValueError("A série recebida está vazia.")

    ordered = df.copy()
    ordered["ds_data"] = pd.to_datetime(ordered["ds_data"])
    ordered = ordered.sort_values("ds_data").reset_index(drop=True)

    # Normaliza as datas para o primeiro dia de cada mês e agrega duplicidades.
    ordered["ds_data"] = ordered["ds_data"].dt.to_period("M").dt.to_timestamp()
    ordered = (
        ordered.groupby("ds_data", as_index=False)
        .agg(
            volume_internacoes=("volume_internacoes", "sum"),
            valor_aprovado=("valor_aprovado", "sum"),
        )
        .sort_values("ds_data")
    )

    full_calendar = pd.date_range(
        start=ordered["ds_data"].min(),
        end=ordered["ds_data"].max(),
        freq="MS",
    )
    series_df = pd.DataFrame({"ds_data": full_calendar}).merge(
        ordered, on="ds_data", how="left"
    )

    missing_count = int(series_df["volume_internacoes"].isna().sum())
    series_df["competencia"] = (
        series_df["ds_data"].dt.strftime("%Y%m").astype(int)
    )
    series_df["ano"] = series_df["ds_data"].dt.year
    series_df["mes"] = series_df["ds_data"].dt.month
    series_df["trimestre"] = ((series_df["mes"] - 1) // 3) + 1

    for column in ("volume_internacoes", "valor_aprovado"):
        series_df[column] = pd.to_numeric(series_df[column], errors="coerce")
        series_df[column] = series_df[column].ffill()
        if series_df[column].isna().any():
            raise ValueError(
                f"A coluna {column!r} possui valores ausentes no início da série. "
                "Não é seguro preenchê-los usando observações futuras."
            )

    if (series_df["volume_internacoes"] < 0).any():
        raise ValueError("O volume de procedimentos não pode ser negativo.")

    time_index = np.arange(len(series_df), dtype=float)
    trend_slope = (
        float(
            np.polyfit(
                time_index,
                series_df["volume_internacoes"].to_numpy(dtype=float),
                1,
            )[0]
        )
        if len(series_df) > 1
        else 0.0
    )

    quarterly_means = (
        series_df.groupby("trimestre")["volume_internacoes"]
        .mean()
        .round(2)
        .to_dict()
    )

    eda_info: dict[str, Any] = {
        "total_months": int(len(series_df)),
        "start_competencia": int(series_df["competencia"].min()),
        "end_competencia": int(series_df["competencia"].max()),
        "missing_months_filled": missing_count,
        "mean_volume": round(float(series_df["volume_internacoes"].mean()), 2),
        "std_volume": round(float(series_df["volume_internacoes"].std(ddof=0)), 2),
        "min_volume": round(float(series_df["volume_internacoes"].min()), 2),
        "max_volume": round(float(series_df["volume_internacoes"].max()), 2),
        "trend_slope_per_month": round(trend_slope, 4),
        "quarterly_seasonality": {
            f"T{quarter}": value
            for quarter, value in quarterly_means.items()
        },
    }
    return series_df, eda_info


def build_time_series_features(series_df: pd.DataFrame) -> pd.DataFrame:
    """Cria lags e médias móveis usando exclusivamente observações anteriores."""
    feat = series_df.copy().sort_values("ds_data").reset_index(drop=True)

    feat["trend_idx"] = np.arange(len(feat), dtype=float)
    feat["month_sin"] = np.sin(2.0 * np.pi * feat["mes"] / 12.0)
    feat["month_cos"] = np.cos(2.0 * np.pi * feat["mes"] / 12.0)

    volume = feat["volume_internacoes"].astype(float)
    feat["lag_1"] = volume.shift(1)
    feat["lag_2"] = volume.shift(2)
    feat["lag_3"] = volume.shift(3)

    previous_values = volume.shift(1)
    feat["rolling_mean_3"] = previous_values.rolling(window=3).mean()
    feat["rolling_std_3"] = (
        previous_values.rolling(window=3).std().fillna(0.0)
    )

    feat = feat.dropna(
        subset=["lag_1", "lag_2", "lag_3", "rolling_mean_3"]
    ).reset_index(drop=True)

    if feat.empty:
        raise ValueError("Não há observações suficientes para criar os atributos temporais.")

    return feat


def compute_regression_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, float]:
    """Calcula MAE, RMSE e MAPE (%)."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    nonzero_mask = np.abs(actual) >= 1e-6
    if nonzero_mask.any():
        mape = float(
            np.mean(
                np.abs(
                    (actual[nonzero_mask] - predicted[nonzero_mask])
                    / actual[nonzero_mask]
                )
            )
            * 100.0
        )
    else:
        mape = float("nan")

    return {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "MAPE_pct": round(mape, 2) if np.isfinite(mape) else float("nan"),
    }


def train_and_evaluate_models(
    df_feat: pd.DataFrame, test_horizon: int = 6
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Faz holdout temporal e validação cruzada temporal no treino.

    A seleção do melhor modelo usa o MAE médio da validação cruzada, não o
    conjunto de teste. O teste fica reservado para a avaliação final.
    """
    if len(df_feat) < 10:
        raise ValueError(
            "Série insuficiente: são necessários ao menos 10 registros "
            "após a engenharia de atributos."
        )

    horizon = min(max(2, int(test_horizon)), len(df_feat) - 6)
    train_df = df_feat.iloc[:-horizon].copy()
    test_df = df_feat.iloc[-horizon:].copy()

    x_train = train_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train_df["volume_internacoes"].to_numpy(dtype=float)
    x_test = test_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_test = test_df["volume_internacoes"].to_numpy(dtype=float)

    baseline_predictions = test_df["lag_1"].to_numpy(dtype=float)
    baseline_metrics = compute_regression_metrics(y_test, baseline_predictions)

    predictions_df = test_df[
        ["competencia", "ds_data", "volume_internacoes"]
    ].copy()
    predictions_df = predictions_df.rename(
        columns={"volume_internacoes": "valor_real"}
    )
    predictions_df["Naive_Lag1_Baseline"] = np.round(
        baseline_predictions, 2
    )

    models = {
        "LinearRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("regressor", LinearRegression()),
            ]
        ),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=100,
            max_depth=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "XGBRegressor": XGBRegressor(
            n_estimators=80,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.9,
            random_state=42,
            verbosity=0,
            n_jobs=-1,
            objective="reg:squarederror",
        ),
    }

    n_splits = min(3, len(train_df) - 1)
    if n_splits < 2:
        raise ValueError("Dados insuficientes para validação cruzada temporal.")

    time_cv = TimeSeriesSplit(n_splits=n_splits)
    results: list[dict[str, Any]] = [
        {
            "model_name": "Naive_Lag1_Baseline",
            "cv_mae_mean": None,
            **baseline_metrics,
        }
    ]

    best_model_name = "Naive_Lag1_Baseline"
    best_cv_mae = float("inf")
    best_model: Any | None = None

    for name, model in models.items():
        fold_maes: list[float] = []

        for train_indices, validation_indices in time_cv.split(x_train):
            model.fit(x_train[train_indices], y_train[train_indices])
            validation_predictions = model.predict(x_train[validation_indices])
            fold_maes.append(
                float(
                    mean_absolute_error(
                        y_train[validation_indices], validation_predictions
                    )
                )
            )

        cv_mae = float(np.mean(fold_maes))

        # Ajusta novamente usando todo o conjunto de treino.
        model.fit(x_train, y_train)
        predictions = np.maximum(0.0, model.predict(x_test))
        predictions_df[name] = np.round(predictions, 2)

        model_metrics = compute_regression_metrics(y_test, predictions)
        results.append(
            {
                "model_name": name,
                "cv_mae_mean": round(cv_mae, 2),
                **model_metrics,
            }
        )

        if cv_mae < best_cv_mae:
            best_cv_mae = cv_mae
            best_model_name = name
            best_model = model

    metrics_df = (
        pd.DataFrame(results)
        .sort_values("RMSE")
        .reset_index(drop=True)
    )

    model_path: str | None = None
    if best_model is not None:
        output_path = Path("ml/models/best_demand_forecast_model.pkl")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as model_file:
            pickle.dump(best_model, model_file)
        model_path = str(output_path)

    best_test_row = metrics_df.loc[
        metrics_df["model_name"] == best_model_name
    ].iloc[0]

    summary_meta: dict[str, Any] = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "train_periods": int(len(train_df)),
        "test_periods": int(len(test_df)),
        "best_model": best_model_name,
        "best_cv_mae": round(best_cv_mae, 2),
        "best_model_test_rmse": float(best_test_row["RMSE"]),
        "baseline_rmse": float(baseline_metrics["RMSE"]),
        "model_path": model_path,
        "selection_criterion": "CV_MAE",
    }

    return metrics_df, predictions_df, summary_meta


def save_forecast_plot_and_report(
    full_df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    eda_info: dict[str, Any],
    summary_meta: dict[str, Any],
) -> None:
    """Salva gráfico, métricas JSON e relatório Markdown."""
    plot_path = Path("docs/screenshots/ml_demand_forecast.png")
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(
        full_df["ds_data"],
        full_df["volume_internacoes"],
        label="Histórico SIH/SUS (DW Gold)",
        color="#1f2937",
        linewidth=2.2,
        marker="o",
        markersize=4,
    )

    ax.plot(
        predictions_df["ds_data"],
        predictions_df["Naive_Lag1_Baseline"],
        label="Baseline (Naive Lag-1)",
        color="#9ca3af",
        linestyle="--",
        linewidth=1.8,
    )

    model_columns = [
        "LinearRegression",
        "RandomForestRegressor",
        "XGBRegressor",
    ]
    model_colors = ["#0284c7", "#16a34a", "#ea580c"]
    for model_name, color in zip(model_columns, model_colors):
        if model_name in predictions_df.columns:
            ax.plot(
                predictions_df["ds_data"],
                predictions_df[model_name],
                label=model_name,
                color=color,
                linewidth=1.8,
                marker="s",
                markersize=4,
            )

    ax.axvline(
        predictions_df["ds_data"].min(),
        color="#dc2626",
        linestyle=":",
        linewidth=1.5,
        label="Início do teste temporal",
    )
    ax.set_title(
        "HealthData Intelligence — Previsão de Demanda Hospitalar (SIH/SUS)",
        fontsize=11,
        fontweight="bold",
    )
    ax.set_xlabel("Competência mensal")
    ax.set_ylabel("Volume de procedimentos hospitalares")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=140)
    plt.close(fig)

    metrics_path = Path("ml/models/evaluation_metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    serializable_predictions = predictions_df.copy()
    serializable_predictions["ds_data"] = (
        serializable_predictions["ds_data"].dt.strftime("%Y-%m-%d")
    )

    report_data = {
        "eda": eda_info,
        "summary": summary_meta,
        "metrics": metrics_df.replace({np.nan: None}).to_dict(orient="records"),
        "test_predictions": serializable_predictions.replace(
            {np.nan: None}
        ).to_dict(orient="records"),
    }
    metrics_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    report_path = Path("docs/ml_evaluation_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_table = metrics_df.to_string(index=False)
    predictions_table = predictions_df.drop(
        columns=["ds_data"]
    ).to_string(index=False)

    md_report = f"""# Relatório Técnico — Previsão de Demanda Hospitalar

## 1. Análise exploratória, tendência e sazonalidade

- **Fonte:** `dw_gold.fact_hospital_production` (SIH/SUS).
- **Janela:** {eda_info['start_competencia']} a {eda_info['end_competencia']} ({eda_info['total_months']} meses).
- **Média mensal:** {eda_info['mean_volume']}.
- **Desvio padrão:** {eda_info['std_volume']}.
- **Mínimo / máximo:** {eda_info['min_volume']} / {eda_info['max_volume']}.
- **Tendência linear:** {eda_info['trend_slope_per_month']} procedimentos/mês.
- **Sazonalidade trimestral:** {json.dumps(eda_info['quarterly_seasonality'], ensure_ascii=False)}.
- **Competências preenchidas:** {eda_info['missing_months_filled']}.

## 2. Engenharia de atributos e validação temporal

- **Atributos:** `lag_1`, `lag_2`, `lag_3`, `rolling_mean_3`, `rolling_std_3`, `month_sin`, `month_cos` e `trend_idx`.
- **Divisão:** {summary_meta['train_periods']} competências para treino e {summary_meta['test_periods']} para teste.
- **Critério de seleção:** MAE médio na validação cruzada temporal.
- **Modelo selecionado:** {summary_meta['best_model']}.
- **MAE médio na validação cruzada:** {summary_meta['best_cv_mae']}.
- **RMSE do modelo selecionado no teste:** {summary_meta['best_model_test_rmse']}.
- **RMSE do baseline:** {summary_meta['baseline_rmse']}.

## 3. Métricas no conjunto de teste

```text
{metrics_table}
```

## 4. Previsões no horizonte de teste

```text
{predictions_table}
```

## 5. Limitações e escopo

- Os resultados dependem da cobertura e da qualidade dos registros disponibilizados pelo endpoint oficial do SIH/SUS.
- Uma série histórica curta pode não capturar ciclos plurianuais ou mudanças estruturais.
- Lacunas internas são preenchidas com o último valor observado (`ffill`); lacunas no início da série interrompem o processamento.
- A avaliação usa previsão de um passo à frente: para cada competência de teste, o lag considera o valor observado da competência anterior.
- O módulo tem finalidade experimental e analítica; não deve ser usado isoladamente para decisões clínicas ou alocação real de recursos.
"""
    report_path.write_text(md_report, encoding="utf-8")

    logger.info(
        "[ML OK] Gráfico: %s | Métricas: %s | Relatório: %s",
        plot_path,
        metrics_path,
        report_path,
    )


def run_ml_pipeline() -> pd.DataFrame:
    """Executa o fluxo completo de preparação, treino, avaliação e documentação."""
    raw_df = load_monthly_series_from_gold()
    series_df, eda_info = explore_trend_seasonality_and_impute(raw_df)
    features_df = build_time_series_features(series_df)

    metrics_df, predictions_df, summary_meta = train_and_evaluate_models(
        features_df,
        test_horizon=6,
    )

    save_forecast_plot_and_report(
        series_df,
        predictions_df,
        metrics_df,
        eda_info,
        summary_meta,
    )

    print(
        "\n=== RESULTADO COMPARATIVO DOS MODELOS "
        "(DADOS DO DW GOLD) ==="
    )
    print(metrics_df.to_string(index=False))
    print(f"\nMelhor modelo (seleção por CV): {summary_meta['best_model']}")
    return metrics_df


if __name__ == "__main__":
    run_ml_pipeline()
