"""
Testes Unitários da Camada Silver e Motor de Qualidade de Dados (Pytest).
"""

import pandas as pd
from src.processing.silver_processor import (
    clean_cnes_estabelecimentos,
    clean_hospitais_e_leitos,
    clean_municipios_saude,
)
from src.validation.quality_rules import apply_quality_rules


def test_quality_rules_separates_valid_and_rejected_without_silent_drop():
    raw_data = pd.DataFrame(
        [
            {"co_ibge": "230440", "nome": "HOSPITAL A", "qt_leitos": 50},
            {"co_ibge": "230440", "nome": "HOSPITAL A DUPLICADO", "qt_leitos": 50},  # Duplicata de chave
            {"co_ibge": "99", "nome": "HOSPITAL IBGE INVALIDO", "qt_leitos": 10},    # IBGE inválido
            {"co_ibge": "230270", "nome": "HOSPITAL LEITO NEGATIVO", "qt_leitos": -5},  # Valor negativo
        ]
    )

    df_valid, df_rejected = apply_quality_rules(
        raw_data,
        required_columns=["co_ibge", "nome"],
        unique_keys=["co_ibge"],
        non_negative_columns=["qt_leitos"],
        ibge_column="co_ibge",
    )

    assert len(df_valid) == 1
    assert len(df_rejected) == 3
    assert len(df_valid) + len(df_rejected) == len(raw_data)
    assert "DUPLICATE_PRIMARY_KEY" in df_rejected.iloc[0]["_rejection_reason"]
    assert "INVALID_IBGE" in df_rejected.iloc[1]["_rejection_reason"]
    assert "NEGATIVE_OR_NAN" in df_rejected.iloc[2]["_rejection_reason"]


def test_clean_cnes_estabelecimentos_zero_fills_cnes_code():
    df_raw = pd.DataFrame(
        [
            {
                "codigo_cnes": 78,
                "codigo_municipio": 260290,
                "codigo_uf": 26,
                "nome_fantasia": " centro herbert de souza ",
                "nome_razao_social": "PREFEITURA MUNICIPAL",
                "tipo_gestao": "m",
                "estabelecimento_faz_atendimento_ambulatorial_sus": "sim",
                "estabelecimento_possui_atendimento_hospitalar": 1,
            }
        ]
    )

    df_valid, df_rejected = clean_cnes_estabelecimentos(df_raw)
    assert len(df_rejected) == 0
    assert len(df_valid) == 1
    assert df_valid.iloc[0]["codigo_cnes"] == "0000078"
    assert df_valid.iloc[0]["nome_fantasia"] == "CENTRO HERBERT DE SOUZA"
    assert df_valid.iloc[0]["tipo_gestao"] == "M"


def test_clean_hospitais_e_leitos_fixes_ministry_typos():
    df_raw = pd.DataFrame(
        [
            {
                "nome_da_regiao_do_brasil_onde_fica_o_hospital": "nordeste",
                "unidade_da_federacao_onde_fica_o_hospital": "ce",
                "nome_do_municipio_onde_fica_o_hospital": "FORTALEZA",
                "nome_do_hospital": "hospital geral de fortaleza",
                "nome_da_razao_social_do_hospital": "SESA CE",
                "tipo_da_gestao_do_hospital": "E",
                "descricao_da_natureza_juridica_do_hosptial": "ADMINISTRACAO PUBLICA",
                "enderco_do_hospital": "RUA AVILA GOULART",
                "numero_do_cep_do_hospital": "60150160",
                "quantidade_total_de_leitos_do_hosptial": "420",
                "quantidade_total_de_leitos_sus_do_hosptial": "400",
                "quantidade_de_leitos_de_uti_do_hosptial": "65",
                "codigo_ibge_do_municipio": 230440,
            }
        ]
    )

    df_valid, df_rejected = clean_hospitais_e_leitos(df_raw)
    assert len(df_rejected) == 0
    assert "qt_leitos_total" in df_valid.columns
    assert "qt_leitos_sus" in df_valid.columns
    assert "endereco_hospital" in df_valid.columns
    assert df_valid.iloc[0]["qt_leitos_total"] == 420
    assert df_valid.iloc[0]["qt_leitos_sus"] == 400


def test_clean_municipios_saude_extracts_clean_city_name():
    df_raw = pd.DataFrame(
        [
            {
                "codigo_municipio": "110006",
                "municipio": "RO - COLORADO DO OESTE",
                "codigo_uf": "11",
                "uf": "Rondônia",
                "regiao_pais": "Norte",
                "macrorregiao_saude": "MACRORREGIONAL II",
                "regiao_saude": "CONE SUL",
                "populacao_estimada_ibge_2022": "15663",
            }
        ]
    )

    df_valid, df_rejected = clean_municipios_saude(df_raw)
    assert len(df_rejected) == 0
    assert df_valid.iloc[0]["nome_municipio"] == "COLORADO DO OESTE"
    assert df_valid.iloc[0]["populacao_estimada_ibge_2022"] == 15663
