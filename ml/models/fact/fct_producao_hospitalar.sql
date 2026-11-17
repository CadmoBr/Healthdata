{{
    config(
        materialized='incremental',
        unique_key=['cnes', 'nu_comp', 'cbo_sigtap']
    )
}}

with silver_sih as (
    select * from {{ ref('silver_sih_producao_hospitalar') }}
    
    {% if is_incremental() %}
    -- Processa apenas registros novos nas execuções incrementais
    where _silver_processed_at > (select max(_silver_processed_at) from {{ this }})
    {% endif %}
),

cleaned_fact as (
    select
        cnes,
        cast(nu_comp as integer) as competencia,
        coalesce(qt_apresentada, 0) as quantidade_apresentada,
        coalesce(vl_apresentado, 0.0) as valor_apresentado,
        ano_particao as ano,
        mes_particao as mes,
        _silver_processed_at
    from silver_sih
)

select * from cleaned_fact