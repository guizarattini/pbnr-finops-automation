import os
import json
import urllib.request
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

# Conexão com o banco PostgreSQL criado na Fase 2
DB_URI = "postgresql+psycopg2://finops_user:btg2027@localhost:5432/finops_btg"
engine = create_engine(DB_URI)

app = FastAPI(
    title="BTG FinOps & Entity Controlling API - Poleiro Blues n' Roll",
    description="API REST em Python + PostgreSQL + IA para Automacao de DRE, Auditoria de Desvios e Simulador P&L.",
    version="1.0.0",
)

# Libera o acesso para o Front-end em React JS (Fase 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DescricaoSujaInput(BaseModel):
    descricao: str
    valor: float


class SimuladorInput(BaseModel):
    delta_publico_pct: float = 0.0
    delta_ticket_pct: float = 0.0
    delta_patrocinio_pct: float = 0.0


@app.get("/api/dre")
def obter_dre_postgresql():
    """1. Consulta a DRE em tempo real direto no PostgreSQL via SQL."""
    query = text("""
        SELECT 
            unidade,
            COUNT(*) AS qtd_lancamentos,
            ROUND(SUM(CASE WHEN tipo = 'RECEITA' THEN valor ELSE 0 END)::numeric, 2) AS receita,
            ROUND(SUM(CASE WHEN tipo = 'CUSTO_PAGO' THEN valor ELSE 0 END)::numeric, 2) AS custo_pago,
            ROUND(SUM(CASE WHEN tipo = 'A_PAGAR' THEN valor ELSE 0 END)::numeric, 2) AS a_pagar,
            ROUND(SUM(
                CASE 
                    WHEN tipo = 'RECEITA' THEN valor
                    WHEN tipo = 'CUSTO_PAGO' THEN -valor
                    ELSE 0 
                END
            )::numeric, 2) AS resultado_caixa_h10,
            ROUND(SUM(
                CASE 
                    WHEN tipo = 'RECEITA' THEN valor
                    WHEN tipo IN ('CUSTO_PAGO', 'A_PAGAR') THEN -valor
                    ELSE 0 
                END
            )::numeric, 2) AS resultado_liquido_h12
        FROM lancamentos_auditados
        GROUP BY unidade
        ORDER BY resultado_liquido_h12 DESC;
    """)
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)

    return {
        "evento": "Poleiro Blues n' Roll 2026",
        "kpis": {
            "total_lancamentos": int(df["qtd_lancamentos"].sum()),
            "receita_total": round(float(df["receita"].sum()), 2),
            "custo_pago_total": round(float(df["custo_pago"].sum()), 2),
            "contas_a_pagar": round(float(df["a_pagar"].sum()), 2),
            "lucro_caixa_h10": round(float(df["resultado_caixa_h10"].sum()), 2),
            "lucro_liquido_h12": round(float(df["resultado_liquido_h12"].sum()), 2),
        },
        "dre_unidades": df.to_dict(orient="records"),
    }


@app.get("/api/auditoria-ia")
def auditar_orcado_vs_realizado():
    """2. Audita os desvios entre a Aba REAL (R$ 16.721,96) e o Executado (R$ 17.871,19) com parecer de IA."""
    desvios = [
        {
            "setor": "Marketing, Grafica & Arte",
            "orcado_aba_real": 780.00,
            "executado_dre": 1541.50,
            "desvio_rs": 761.50,
            "desvio_pct": 97.63,
            "causa_raiz": "Permuta Blin (R$ 392,50) + impressao extra (R$ 369,00) zeradas na aba REAL.",
        },
        {
            "setor": "Bar & Alimentacao (c/ Paiol)",
            "orcado_aba_real": 4411.25,
            "executado_dre": 5011.25,
            "desvio_rs": 600.00,
            "desvio_pct": 13.60,
            "causa_raiz": "Permuta de 5 fardos de Xeque Mate Eneas (R$ 600,00) lancada no Fluxo de Caixa.",
        },
        {
            "setor": "Merchandising (Camisas & Copos)",
            "orcado_aba_real": 2429.50,
            "executado_dre": 2469.50,
            "desvio_rs": 40.00,
            "desvio_pct": 1.65,
            "causa_raiz": "Estorno/reembolso de 1 camisa avulsa (R$ 40,00 - linha 258).",
        },
        {
            "setor": "Atracoes (SOAD + Seven Heads)",
            "orcado_aba_real": 4280.00,
            "executado_dre": 4280.00,
            "desvio_rs": 0.00,
            "desvio_pct": 0.00,
            "causa_raiz": "100% aderente ao orcamento.",
        },
        {
            "setor": "Juridico (Alvaras)",
            "orcado_aba_real": 181.21,
            "executado_dre": 181.21,
            "desvio_rs": 0.00,
            "desvio_pct": 0.00,
            "causa_raiz": "100% aderente ao orcamento.",
        },
        {
            "setor": "Estrutura & Seguranca (c/ Uber R$ 160)",
            "orcado_aba_real": 4640.00,
            "executado_dre": 4387.73,
            "desvio_rs": -252.27,
            "desvio_pct": -5.44,
            "causa_raiz": "Economia operacional de R$ 252,27 mesmo corrigindo os R$ 160,00 fora do SUMIF.",
        },
    ]

    parecer_ia = gerar_parecer_ia(desvios)
    return {
        "resumo_orcamentario": {
            "orcado_total_sem_tocha": 16721.96,
            "executado_total_competencia": 17871.19,
            "desvio_liquido_rs": 1149.23,
            "desvio_liquido_pct": 6.87,
        },
        "desvios_por_setor": desvios,
        "parecer_executivo_ia": parecer_ia,
    }


def gerar_parecer_ia(desvios):
    """Chama a API do Gemini se GEMINI_API_KEY estiver configurada; caso contrario, usa o motor deterministico."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            prompt = (
                "Atue como analista de Entity Controlling do BTG Pactual. "
                "Resuma em 3 pontos executivos a auditoria de desvios abaixo: "
                f"{json.dumps(desvios, ensure_ascii=False)}"
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
                return {
                    "motor": "Google Gemini LLM API",
                    "insights": dados["candidates"][0]["content"]["parts"][0]["text"],
                }
        except Exception:
            pass

    return {
        "motor": "FinOps AI Rule Engine (Fallback Ativo)",
        "insights": [
            "1. Efeito Permuta no Desvio (+R$ 1.149,23 / +6,87%): 86,4% do desvio bruto (R$ 992,50) vem da contabilizacao no Fluxo de Caixa das permutas de bebida (Eneas R$ 600,00) e grafica (Blin R$ 392,50), que estavam zeradas na aba REAL.",
            "2. Risco de Planilha Manual: Corrigido furo de SUMIF de R$ 160,00 (Uber Tatuador sem tag de setor na linha 16) e provisionado passivo aberto de R$ 442,05 (Coxinhas Itatiaia).",
            "3. Alavancagem Operacional no Bar: Os 15 combos de camisa/copo se pagaram em 105,4% (R$ 2.603,40 vs R$ 2.469,50) e geraram R$ 38,25 de consumo medio no bar por pessoa (margem de caixa de 53,2%).",
        ],
    }


@app.post("/api/classificar-lancamento")
def classificar_lancamento_sujo(item: DescricaoSujaInput):
    """3. Recebe uma descricao nao padronizada e retorna o desmembramento contabil automatico."""
    desc = item.descricao.upper()
    if "CAMISA" in desc and "INGRESSO" in desc:
        qtd_camisas = 2 if "2 CAMISAS" in desc else 1
        qtd_copos = 2 if "2 COPOS" in desc else (1 if "COPO" in desc else 0)
        valor_merch = round(qtd_camisas * 29.90 + qtd_copos * 5.00, 2)
        valor_bilheteria = round(item.valor - valor_merch, 2)
        return {
            "descricao_original": item.descricao,
            "regra_aplicada": "SPLIT_COMBO_LOSS_LEADER",
            "lancamentos_gerados": [
                {"unidade": "Merchandising (Camisas & Copos)", "tipo": "RECEITA", "valor": valor_merch},
                {"unidade": "Bilheteria (Pix + Cheers + Combos)", "tipo": "RECEITA", "valor": valor_bilheteria},
            ],
        }
    return {
        "descricao_original": item.descricao,
        "regra_aplicada": "CLASSIFICACAO_DIRETA",
        "lancamentos_gerados": [
            {
                "unidade": "Bar & Alimentacao" if any(k in desc for k in ["BAR", "CHOPP", "GELO", "XEQUE"]) else "Bilheteria (Pix + Cheers + Combos)",
                "tipo": "RECEITA" if item.valor >= 0 else "CUSTO_PAGO",
                "valor": abs(item.valor),
            }
        ],
    }


@app.post("/api/simular-2027")
def simular_cenario_2027(sim: SimuladorInput):
    """4. Simulador What-If sobre o baseline auditado de 2026 (reproduz R$ 6.002,47 em 0%)."""
    rec_bilheteria = round(5991.60 * (1 + sim.delta_publico_pct / 100.0) * (1 + sim.delta_ticket_pct / 100.0), 2)
    rec_patrocinio = round(5311.50 * (1 + sim.delta_patrocinio_pct / 100.0), 2)
    lucro_bar = round(4741.96 * (1 + sim.delta_publico_pct / 100.0), 2)
    saldo_merch_outros = 347.85   # R$ 133,90 (Merch) + R$ 213,95 (Outras Entradas)
    custos_fixos = 10390.44       # R$ 4.387,73 (Estrutura) + R$ 4.280,00 (Atracoes) + R$ 1.541,50 (Mkt) + R$ 181,21 (Juridico)

    lucro_projetado = round(rec_bilheteria + rec_patrocinio + lucro_bar + saldo_merch_outros - custos_fixos, 2)
    return {
        "baseline_2026_lucro_liquido": 6002.47,
        "projecao_2027": {
            "receita_bilheteria": rec_bilheteria,
            "receita_patrocinio": rec_patrocinio,
            "lucro_liquido_bar": lucro_bar,
            "custos_fixos": custos_fixos,
            "lucro_liquido_projetado": lucro_projetado,
            "variacao_vs_2026_rs": round(lucro_projetado - 6002.47, 2),
        },
    }