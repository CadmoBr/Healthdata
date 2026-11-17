WITH date_spine AS (
    SELECT
        generate_series(
            DATE '2008-01-01',
            DATE '2026-12-01',
            INTERVAL '1 month'
        )::DATE AS reference_date
)
SELECT
    CAST(TO_CHAR(reference_date, 'YYYYMM') AS INTEGER) AS sk_date,
    reference_date,
    EXTRACT(YEAR FROM reference_date)::INTEGER AS ano,
    EXTRACT(MONTH FROM reference_date)::INTEGER AS mes,
    TO_CHAR(reference_date, 'YYYY-MM') AS ano_mes,
    CEIL(EXTRACT(MONTH FROM reference_date) / 3.0)::INTEGER AS trimestre,
    CASE
        WHEN EXTRACT(MONTH FROM reference_date) <= 6 THEN 1
        ELSE 2
    END AS semestre
FROM date_spine