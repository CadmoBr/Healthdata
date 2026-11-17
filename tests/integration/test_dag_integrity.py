from pathlib import Path
from dags.healthdata_pipeline import DEFAULT_ARGS, PIPELINE_TASK_ORDER
from src.utils.pipeline_reporter import validate_bronze_raw_files


def test_dag_expected_tasks_and_retry_configuration():
    expected = [
        "start_pipeline",
        "extract_cnes",
        "extract_hospital_production",
        "validate_raw_data",
        "process_silver",
        "run_dbt_models",
        "run_data_quality_tests",
        "update_warehouse",
        "generate_pipeline_report",
        "end_pipeline",
    ]
    assert PIPELINE_TASK_ORDER == expected
    assert DEFAULT_ARGS["retries"] >= 2


def test_bronze_raw_files_validation_passes():
    summary = validate_bronze_raw_files()
    assert "cnes_estabelecimentos" in summary
    assert summary["cnes_estabelecimentos"] > 0
    assert Path("dbt/healthdata_dw/dbt_project.yml").exists()