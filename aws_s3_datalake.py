import hashlib
import json
import os
from datetime import datetime, timezone
import pandas as pd

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    BOTO3_DISPONIVEL = True
except ImportError:
    BOTO3_DISPONIVEL = False

ARQUIVO_RAW = "PBNR 2026.xlsx"
ARQUIVO_AUDITADO = "PBNR_2026_DRE_Auditada.xlsx"
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "btg-finops-entity-controlling-pbnr")
AWS_REGION = os.getenv("AWS_REGION", "sa-east-1")
LOCAL_S3_MIRROR = "aws_s3_mirror"


def calcular_sha256(caminho_arquivo: str) -> str:
    """Gera o hash criptografico SHA-256 para trilha de auditoria (Compliance Financeiro)."""
    sha256 = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def extrair_metricas_auditoria(caminho_raw: str, caminho_audit: str) -> dict:
    """Inspeciona as abas dos ficheiros Excel e extrai estatisticas descritivas para o Manifesto S3."""
    xls_raw = pd.ExcelFile(caminho_raw)
    xls_audit = pd.ExcelFile(caminho_audit)

    df_lanc = pd.read_excel(xls_audit, sheet_name="Lancamentos_Auditados")
    df_dre = pd.read_excel(xls_audit, sheet_name="DRE_Consolidada")

    # Deteta automaticamente o nome das colunas de resultado na folha de calculo
    col_caixa = "RESULTADO_CAIXA_H10" if "RESULTADO_CAIXA_H10" in df_dre.columns else "RESULTADO_CAIXA"
    col_liq = "RESULTADO_LIQUIDO_H12" if "RESULTADO_LIQUIDO_H12" in df_dre.columns else "RESULTADO_LIQUIDO"

    stats_lanc = df_lanc["valor"].agg(["count", "mean", "median", "min", "max", "std", "sum"])
    stats_rec = df_dre["RECEITA"].agg(["count", "mean", "median", "min", "max", "std", "sum"])
    stats_custo = df_dre["CUSTO_PAGO"].agg(["count", "mean", "median", "min", "max", "std", "sum"])
    stats_liq = df_dre[col_liq].agg(["count", "mean", "median", "min", "max", "std", "sum"])

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entidade": "Republica Poleiro dos Anjos - PBNR 2026",
        "arquitetura_cloud": "AWS S3 Medallion Data Lake (Bronze / Silver / Gold)",
        "integridade_arquivos": {
            "bronze_raw_file": caminho_raw,
            "bronze_abas_count": len(xls_raw.sheet_names),
            "bronze_size_kb": round(os.path.getsize(caminho_raw) / 1024.0, 2),
            "bronze_sha256": calcular_sha256(caminho_raw),
            "gold_audit_file": caminho_audit,
            "gold_abas_count": len(xls_audit.sheet_names),
            "gold_size_kb": round(os.path.getsize(caminho_audit) / 1024.0, 2),
            "gold_sha256": calcular_sha256(caminho_audit),
        },
        "estatisticas_transacionais_silver": {
            "total_lancamentos": int(stats_lanc["count"]),
            "volume_bruto_movimentado_rs": round(float(stats_lanc["sum"]), 2),
            "media_rs": round(float(stats_lanc["mean"]), 2),
            "mediana_rs": round(float(stats_lanc["median"]), 2),
            "minimo_rs": round(float(stats_lanc["min"]), 2),
            "maximo_rs": round(float(stats_lanc["max"]), 2),
            "desvio_padrao_rs": round(float(stats_lanc["std"]), 2),
        },
        "estatisticas_dre_gold": {
            "unidades_negocio_count": int(stats_rec["count"]),
            "receita_total_rs": round(float(stats_rec["sum"]), 2),
            "receita_media_rs": round(float(stats_rec["mean"]), 2),
            "receita_mediana_rs": round(float(stats_rec["median"]), 2),
            "receita_std_rs": round(float(stats_rec["std"]), 2),
            "custo_pago_total_rs": round(float(stats_custo["sum"]), 2),
            "custo_pago_medio_rs": round(float(stats_custo["mean"]), 2),
            "contas_a_pagar_rs": round(float(df_dre["A_PAGAR"].sum()), 2),
            "lucro_caixa_h10_rs": round(float(df_dre[col_caixa].sum()), 2),
            "lucro_liquido_h12_rs": round(float(stats_liq["sum"]), 2),
            "lucro_liquido_medio_rs": round(float(stats_liq["mean"]), 2),
            "lucro_liquido_mediana_rs": round(float(stats_liq["median"]), 2),
            "lucro_liquido_std_rs": round(float(stats_liq["std"]), 2),
        },
    }


def sincronizar_datalake_s3():
    """Executa o pipeline de ingestao para AWS S3 (Bronze, Silver e Gold) com criptografia AES-256."""
    manifesto = extrair_metricas_auditoria(ARQUIVO_RAW, ARQUIVO_AUDITADO)
    xls_audit = pd.ExcelFile(ARQUIVO_AUDITADO)
    df_lanc = pd.read_excel(xls_audit, sheet_name="Lancamentos_Auditados")
    df_dre = pd.read_excel(xls_audit, sheet_name="DRE_Consolidada")

    for camada in ["bronze/ano=2026", "silver/ano=2026", "gold/ano=2026"]:
        os.makedirs(os.path.join(LOCAL_S3_MIRROR, camada), exist_ok=True)

    caminho_silver_csv = os.path.join(LOCAL_S3_MIRROR, "silver/ano=2026/lancamentos_auditados.csv")
    caminho_gold_dre_json = os.path.join(LOCAL_S3_MIRROR, "gold/ano=2026/dre_consolidada.json")
    caminho_manifesto = os.path.join(LOCAL_S3_MIRROR, "gold/ano=2026/s3_audit_manifest.json")

    df_lanc.to_csv(caminho_silver_csv, index=False, encoding="utf-8")
    df_dre.to_json(caminho_gold_dre_json, orient="records", indent=2, force_ascii=False)
    with open(caminho_manifesto, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, indent=2, ensure_ascii=False)

    objetos_s3 = [
        (ARQUIVO_RAW, "bronze/ano=2026/PBNR_2026_raw.xlsx"),
        (caminho_silver_csv, "silver/ano=2026/lancamentos_auditados.csv"),
        (ARQUIVO_AUDITADO, "gold/ano=2026/PBNR_2026_DRE_Auditada.xlsx"),
        (caminho_gold_dre_json, "gold/ano=2026/dre_consolidada.json"),
        (caminho_manifesto, "gold/ano=2026/s3_audit_manifest.json"),
    ]

    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    modo_execucao = "LOCAL_S3_MIRROR (Simulacao Offline / Sem Credenciais AWS Ativas)"

    if BOTO3_DISPONIVEL and aws_key:
        try:
            s3_client = boto3.client("s3", region_name=AWS_REGION)
            for arquivo_local, s3_key in objetos_s3:
                s3_client.upload_file(
                    Filename=arquivo_local,
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    ExtraArgs={
                        "ServerSideEncryption": "AES256",
                        "Metadata": {
                            "entidade": "pbnr-2026",
                            "sha256": calcular_sha256(arquivo_local),
                            "lucro-liquido-h12": str(manifesto["estatisticas_dre_gold"]["lucro_liquido_h12_rs"]),
                        },
                    },
                )
            modo_execucao = f"AWS_S3_CLOUD_LIVE (s3://{S3_BUCKET_NAME})"
        except (NoCredentialsError, ClientError, BotoCoreError) as err:
            modo_execucao = f"FALLBACK_LOCAL_MIRROR (Aviso AWS: {type(err).__name__})"

    print("=== AWS S3 FINOPS DATA LAKE - RELATORIO DE SINCRONIZACAO ===")
    print(f"Modo de Operacao: {modo_execucao}")
    print(f"Bucket Alvo:      s3://{S3_BUCKET_NAME} (Regiao: {AWS_REGION})")
    print("-" * 72)
    for arq_local, s3_key in objetos_s3:
        tam_kb = os.path.getsize(arq_local) / 1024.0
        sha_curto = calcular_sha256(arq_local)[:12]
        print(f"[S3 OBJECT] s3://{S3_BUCKET_NAME}/{s3_key:<42} | {tam_kb:>6.2f} KB | SHA256: {sha_curto}...")
    print("-" * 72)
    print(f"BRONZE (Bruto):   {manifesto['integridade_arquivos']['bronze_abas_count']} abas | {manifesto['integridade_arquivos']['bronze_size_kb']} KB")
    print(f"SILVER (Limpo):   {manifesto['estatisticas_transacionais_silver']['total_lancamentos']} lancamentos | Media: R$ {manifesto['estatisticas_transacionais_silver']['media_rs']} | Mediana: R$ {manifesto['estatisticas_transacionais_silver']['mediana_rs']}")
    print(f"GOLD (DRE Final): {manifesto['estatisticas_dre_gold']['unidades_negocio_count']} centros | Receita: R$ {manifesto['estatisticas_dre_gold']['receita_total_rs']:,.2f} | Liquido H12: R$ {manifesto['estatisticas_dre_gold']['lucro_liquido_h12_rs']:,.2f}")
    return manifesto


if __name__ == "__main__":
    sincronizar_datalake_s3()