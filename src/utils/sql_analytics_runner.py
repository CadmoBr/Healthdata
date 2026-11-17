"""
Executor das Consultas Analíticas SQL sobre a Camada Gold (dw_gold).
Executa todas as consultas definidas em `sql/queries/analytical_queries.sql` usando sqlalchemy.text()
e gera relatório Markdown em `docs/sql_analytics_results.md`.
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.utils.db import get_db_engine
from src.utils.logger import get_logger

logger = get_logger("sql_analytics_runner")


def run_analytical_queries() -> None:
    sql_file = Path("sql/queries/analytical_queries.sql")
    raw_sql = sql_file.read_text(encoding="utf-8")

    statements = [s.strip() for s in raw_sql.split(";") if s.strip()]
    engine = get_db_engine()

    md_lines = [
        "# Resultados das Consultas Analíticas SQL — Camada Gold (`dw_gold`)\n",
        "Consultas executadas diretamente sobre o Star Schema no PostgreSQL.\n",
    ]

    with engine.connect() as conn:
        for idx, stmt in enumerate(statements, start=1):
            title_line = f"Query Analítica #{idx}"
            for line in stmt.splitlines():
                if line.strip().startswith("-- [QUERY"):
                    title_line = line.strip().replace("-- ", "")
                    break

            logger.info(f"Executando {title_line}...")
            df = pd.read_sql(text(stmt), conn)

            print("\n=====================================================================")
            print(f"{title_line} ({len(df)} linhas retornadas)")
            print("=====================================================================")
            print(df.to_string(index=False))

            md_lines.append(f"## {title_line}\n")
            md_lines.append("```text")
            md_lines.append(df.to_string(index=False))
            md_lines.append("```\n")

    out_md = Path("docs/sql_analytics_results.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"Relatório analítico SQL salvo com sucesso em: {out_md}")


if __name__ == "__main__":
    run_analytical_queries()