import pandas as pd

from ml.src import demand_forecasting


def test_load_gold_data_aggregates_existing_fact_columns_by_date(monkeypatch):
    engine = object()
    expected = pd.DataFrame(
        {
            "competencia": [202601],
            "ano": [2026],
            "mes": [1],
            "total_producao": [125],
            "total_valor": [2500.0],
        }
    )
    captured = {}

    def fake_read_sql(query, con):
        captured["query"] = " ".join(query.split())
        captured["connection"] = con
        return expected

    monkeypatch.setattr(demand_forecasting, "get_db_engine", lambda: engine)
    monkeypatch.setattr(demand_forecasting.pd, "read_sql", fake_read_sql)

    result = demand_forecasting.load_gold_data()

    assert captured["connection"] is engine
    assert "SUM(p.qt_procedimento) AS total_producao" in captured["query"]
    assert "SUM(p.vl_procedimento) AS total_valor" in captured["query"]
    assert "ON p.fk_date = d.sk_date" in captured["query"]
    pd.testing.assert_frame_equal(result, expected)
