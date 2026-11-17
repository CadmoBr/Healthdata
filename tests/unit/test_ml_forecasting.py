"""Testes unitários do módulo de previsão de demanda hospitalar."""

import numpy as np
import pandas as pd

from ml.src.demand_forecasting import (
    build_time_series_features,
    explore_trend_seasonality_and_impute,
    train_and_evaluate_models,
)


def make_sample_series(periods: int = 36) -> pd.DataFrame:
    dates = pd.date_range("2017-01-01", periods=periods, freq="MS")
    month = dates.month.to_numpy()
    trend = np.arange(periods, dtype=float)
    volume = 1000 + trend * 8 + 100 * np.sin(2 * np.pi * month / 12)

    return pd.DataFrame(
        {
            "competencia": dates.strftime("%Y%m").astype(int),
            "ds_data": dates,
            "ano": dates.year,
            "mes": dates.month,
            "trimestre": ((dates.month - 1) // 3) + 1,
            "volume_internacoes": volume,
            "valor_aprovado": volume * 125.0,
        }
    )


def test_feature_engineering_uses_only_previous_values():
    raw_df = make_sample_series()
    series_df, _ = explore_trend_seasonality_and_impute(raw_df)
    features = build_time_series_features(series_df)

    assert len(features) == len(series_df) - 3
    assert features["lag_1"].notna().all()
    assert features["lag_2"].notna().all()
    assert features["lag_3"].notna().all()
    assert features.iloc[0]["lag_1"] == series_df.iloc[2]["volume_internacoes"]
    assert features.iloc[0]["rolling_mean_3"] == series_df.iloc[:3][
        "volume_internacoes"
    ].mean()


def test_temporal_model_evaluation_returns_expected_metrics():
    raw_df = make_sample_series()
    series_df, _ = explore_trend_seasonality_and_impute(raw_df)
    features = build_time_series_features(series_df)

    metrics_df, predictions_df, metadata = train_and_evaluate_models(
        features,
        test_horizon=4,
    )

    expected_models = {
        "Naive_Lag1_Baseline",
        "LinearRegression",
        "RandomForestRegressor",
        "XGBRegressor",
    }
    assert set(metrics_df["model_name"]) == expected_models
    assert len(predictions_df) == 4
    assert {"MAE", "RMSE", "MAPE_pct"}.issubset(metrics_df.columns)
    assert metadata["train_periods"] > metadata["test_periods"]