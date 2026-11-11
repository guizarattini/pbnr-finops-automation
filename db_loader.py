import pandas as pd
from sqlalchemy import create_engine, text

# String de conexão com o banco PostgreSQL local no WSL
DB_URI = "postgresql+psycopg2://finops_user:btg2027@localhost:5432/finops_btg"
ARQUIVO_AUDITADO = "PBNR_2026_DRE_Auditada.xlsx"


def carregar_para_postgresql():
    engine = create_engine(DB_URI)

    # 1. Lê as duas abas da planilha auditada gerada na Fase 1
    df_lanc = pd.read_excel(ARQUIVO_AUDITADO, sheet_name="Lancamentos_Auditados")
    df_dre = pd.read_excel(ARQUIVO_AUDITADO, sheet_name="DRE_Consolidada")

    # 2. Adiciona metadados de Multi-Entidade (Padrão Entity Controlling BTG)
    df_lanc["evento_nome"] = "Poleiro Blues n' Roll"
    df_lanc["edicao_ano"] = 2026
    df_dre["evento_nome"] = "Poleiro Blues n' Roll"
    df_dre["edicao_ano"] = 2026

    # 3. Grava as tabelas diretamente no PostgreSQL
    df_lanc.to_sql("lancamentos_auditados", engine, if_exists="replace", index=False)
    df_dre.to_sql("dre_consolidada", engine, if_exists="replace", index=False)
    print(f"[OK] {len(df_lanc)} lancamentos e {len(df_dre)} linhas de DRE gravados no PostgreSQL!\n")

    # 4. Executa uma consulta SQL analítica real direto no banco para validar
    query_sql = text("""
        SELECT 
            unidade,
            COUNT(*) AS qtd_lancamentos,
            ROUND(SUM(CASE WHEN tipo = 'RECEITA' THEN valor ELSE 0 END)::numeric, 2) AS receita_sql,
            ROUND(SUM(CASE WHEN tipo = 'CUSTO_PAGO' THEN valor ELSE 0 END)::numeric, 2) AS custo_pago_sql,
            ROUND(SUM(CASE WHEN tipo = 'A_PAGAR' THEN valor ELSE 0 END)::numeric, 2) AS a_pagar_sql,
            ROUND(SUM(
                CASE 
                    WHEN tipo = 'RECEITA' THEN valor
                    WHEN tipo IN ('CUSTO_PAGO', 'A_PAGAR') THEN -valor
                    ELSE 0 
                END
            )::numeric, 2) AS lucro_liquido_sql
        FROM lancamentos_auditados
        WHERE edicao_ano = 2026
        GROUP BY unidade
        ORDER BY lucro_liquido_sql DESC;
    """)

    with engine.connect() as conn:
        df_resultado_sql = pd.read_sql_query(query_sql, conn)

    print("=== CONSULTA SQL EXECUTADA DIRETO NO POSTGRESQL (TABELA: lancamentos_auditados) ===")
    print(df_resultado_sql.to_string(index=False))
    print("-" * 82)
    print(f"TOTAL LANCAMENTOS AUDITADOS NO BANCO: {df_resultado_sql['qtd_lancamentos'].sum()}")
    print(f"LUCRO LIQUIDO CALCULADO VIA SQL:      R$ {df_resultado_sql['lucro_liquido_sql'].sum():,.2f}")


if __name__ == "__main__":
    carregar_para_postgresql()
