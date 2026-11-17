"""
Módulo de Validação e Qualidade de Dados da Camada Silver.
Aplica regras explícitas e auditáveis sem eliminar registros silenciosamente:
separa os registros em (df_valid, df_rejected) documentando a regra violada em `_rejection_reason`.
"""

from typing import List, Tuple
import pandas as pd


def apply_quality_rules(
    df: pd.DataFrame,
    required_columns: List[str],
    unique_keys: List[str],
    non_negative_columns: List[str] | None = None,
    ibge_column: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Avalia regras de qualidade linha a linha e retorna (df_valid, df_rejected).
    Registros duplicados na chave única são marcados como DUPLICATE_KEY_REJECTED.
    """
    if df.empty:
        return df.copy(), pd.DataFrame()

    working_df = df.copy()
    reasons = pd.Series([""] * len(working_df), index=working_df.index, dtype="object")

    # Regra 1: Campos obrigatórios não nulos e não vazios
    for col in required_columns:
        if col not in working_df.columns:
            reasons = reasons + f"MISSING_COLUMN:{col};"
        else:
            is_null = working_df[col].isna() | (working_df[col].astype(str).str.strip() == "") | (
                working_df[col].astype(str).str.lower() == "none"
            )
            reasons.loc[is_null] = reasons.loc[is_null] + f"NULL_REQUIRED:{col};"

    # Regra 2: Consistência do código IBGE municipal (6 dígitos numéricos)
    if ibge_column and ibge_column in working_df.columns:
        ibge_str = working_df[ibge_column].astype(str).str.strip()
        invalid_ibge = ~ibge_str.str.match(r"^\d{6}$")
        reasons.loc[invalid_ibge] = reasons.loc[invalid_ibge] + f"INVALID_IBGE:{ibge_column};"

    # Regra 3: Valores numéricos dentro de limites plausíveis (>= 0)
    if non_negative_columns:
        for num_col in non_negative_columns:
            if num_col in working_df.columns:
                num_vals = pd.to_numeric(working_df[num_col], errors="coerce")
                invalid_num = num_vals.isna() | (num_vals < 0)
                reasons.loc[invalid_num] = (
                    reasons.loc[invalid_num] + f"NEGATIVE_OR_NAN:{num_col};"
                )

    # Regra 4: Unicidade de chave primária/natural (mantém a primeira ocorrência, audita duplicatas)
    valid_unique_cols = [c for c in unique_keys if c in working_df.columns]
    if valid_unique_cols:
        is_dup = working_df.duplicated(subset=valid_unique_cols, keep="first")
        reasons.loc[is_dup] = reasons.loc[is_dup] + "DUPLICATE_PRIMARY_KEY;"

    working_df["_rejection_reason"] = reasons.str.rstrip(";")

    mask_rejected = working_df["_rejection_reason"] != ""
    df_rejected = working_df.loc[mask_rejected].copy()
    df_valid = working_df.loc[~mask_rejected].drop(columns=["_rejection_reason"]).copy()

    return df_valid, df_rejected
