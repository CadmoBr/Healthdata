-- ============================================================================
-- HEALTHDATA INTELLIGENCE - INICIALIZAÇÃO DO DATA WAREHOUSE E OBSERVABILIDADE
-- ============================================================================

-- 1. Criação dos Schemas da Arquitetura Medallion no PostgreSQL
CREATE SCHEMA IF NOT EXISTS raw_silver;
CREATE SCHEMA IF NOT EXISTS dw_gold;

-- 2. Tabela de Observabilidade e Auditoria de Pipelines (Seção 11)
CREATE TABLE IF NOT EXISTS public.pipeline_execution_log (
    execution_id VARCHAR(64) PRIMARY KEY,
    pipeline_name VARCHAR(120) NOT NULL,
    layer VARCHAR(30) NOT NULL,
    dataset_name VARCHAR(80) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10, 2),
    execution_status VARCHAR(30) NOT NULL,
    records_extracted INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    output_path TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_log_status ON public.pipeline_execution_log(execution_status);
CREATE INDEX IF NOT EXISTS idx_pipeline_log_dataset ON public.pipeline_execution_log(dataset_name, start_time DESC);
