import unicodedata
import openpyxl
import pandas as pd

ARQUIVO_ENTRADA = "PBNR 2026.xlsx"
ARQUIVO_SAIDA = "PBNR_2026_DRE_Auditada.xlsx"

CUSTO_UNIT_CAMISA = 29.90
CUSTO_UNIT_COPO = 5.00

def normalizar_texto(texto):
    if texto is None: return "SEM_CLASSIFICACAO"
    texto_str = str(texto).strip().upper()
    if not texto_str or texto_str == "NONE": return "SEM_CLASSIFICACAO"
    return "".join(c for c in unicodedata.normalize("NFD", texto_str) if unicodedata.category(c) != "Mn")

def extrair_fluxo_caixa(caminho_xlsx):
    wb = openpyxl.load_workbook(caminho_xlsx, data_only=True)
    ws = wb["FLUXO DE CAIXA "]
    lancamentos = []
    
    for linha in range(3, ws.max_row + 1):
        data = ws.cell(linha, 1).value
        valor = ws.cell(linha, 2).value
        razao = ws.cell(linha, 5).value
        if valor is not None:
            lancamentos.append({
                "linha_excel": linha,
                "valor": float(valor),
                "razao_norm": normalizar_texto(razao),
            })
            
    extras = {
        "rendimento_conta": float(ws["J2"].value or 0.0),
        "cheers_retido": float(ws["H6"].value or 0.0),
        "patrocinio_pendente": float(ws["H7"].value or 0.0),
        "bar_especie_fisico": float(ws["H8"].value or 0.0),
        "contas_a_pagar_coxinha": float(ws["H11"].value or 0.0)
    }
    return pd.DataFrame(lancamentos), extras

def classificar_e_desmembrar(df_tx, extras):
    registros_dre = []
    for _, row in df_tx.iterrows():
        r = row["razao_norm"]
        val = row["valor"]
        lin = row["linha_excel"]

        # Split Automático de Combos (Loss-Leader)
        if r in ["INGRESSO + CAMISA", "CAMISA + INGRESSO"]:
            registros_dre.extend([
                {"linha": lin, "unidade": "Merchandising (Camisas & Copos)", "tipo": "RECEITA", "valor": CUSTO_UNIT_CAMISA},
                {"linha": lin, "unidade": "Bilheteria (Pix + Cheers)", "tipo": "RECEITA", "valor": val - CUSTO_UNIT_CAMISA}
            ])
        elif r == "2 CAMISAS, 1 IF E 1 IM E 2 COPOS":
            custo_m = (2 * CUSTO_UNIT_CAMISA) + (2 * CUSTO_UNIT_COPO)
            registros_dre.extend([
                {"linha": lin, "unidade": "Merchandising (Camisas & Copos)", "tipo": "RECEITA", "valor": custo_m},
                {"linha": lin, "unidade": "Bilheteria (Pix + Cheers)", "tipo": "RECEITA", "valor": val - custo_m}
            ])
        elif r == "1 CAMISA E 2 INGRESSOS":
            registros_dre.extend([
                {"linha": lin, "unidade": "Merchandising (Camisas & Copos)", "tipo": "RECEITA", "valor": CUSTO_UNIT_CAMISA},
                {"linha": lin, "unidade": "Bilheteria (Pix + Cheers)", "tipo": "RECEITA", "valor": val - CUSTO_UNIT_CAMISA}
            ])
        
        # Conciliação pós-evento
        elif r == "SEM_CLASSIFICACAO":
            if val == 5181.00: registros_dre.append({"linha": lin, "unidade": "Bar & Alimentacao", "tipo": "RECEITA", "valor": val})
            elif val == 13.00: registros_dre.append({"linha": lin, "unidade": "Bar & Alimentacao", "tipo": "RECEITA", "valor": val})
            elif val == -2840.00: registros_dre.append({"linha": lin, "unidade": "Bar & Alimentacao", "tipo": "CUSTO_PAGO", "valor": abs(val)})
            elif val == -160.00: registros_dre.append({"linha": lin, "unidade": "Estrutura & Seguranca", "tipo": "CUSTO_PAGO", "valor": abs(val)})
        
        # Outras Receitas
        elif val > 0:
            if r in ["INGRESSO", "INGRESSOS DO CHEERS", "RECEBIMENTO DE DINHEIRO"]: registros_dre.append({"linha": lin, "unidade": "Bilheteria (Pix + Cheers)", "tipo": "RECEITA", "valor": val})
            elif r in ["BAR PIX", "DINHEIRO DA KS"]: registros_dre.append({"linha": lin, "unidade": "Bar & Alimentacao", "tipo": "RECEITA", "valor": val})
            elif r == "PATROCINIO": registros_dre.append({"linha": lin, "unidade": "Patrocinios & Permutas", "tipo": "RECEITA", "valor": val})
            elif r == "CAMISA": registros_dre.append({"linha": lin, "unidade": "Merchandising (Camisas & Copos)", "tipo": "RECEITA", "valor": val})
            else: registros_dre.append({"linha": lin, "unidade": "Outras Entradas Operacionais", "tipo": "RECEITA", "valor": val})
        
        # Custos Pagos
        else:
            custo = abs(val)
            if r in ["BAR", "5 FARDOS DE XEQUE MATE", "GELO", "PAYOL"]: registros_dre.append({"linha": lin, "unidade": "Bar & Alimentacao", "tipo": "CUSTO_PAGO", "valor": custo})
            elif r in ["UOMINE", "CAMISA", "COPO", "REEMBOLSO CAMISA"]: registros_dre.append({"linha": lin, "unidade": "Merchandising (Camisas & Copos)", "tipo": "CUSTO_PAGO", "valor": custo})
            elif r == "ATRACAO": registros_dre.append({"linha": lin, "unidade": "Atracoes (Bandas)", "tipo": "CUSTO_PAGO", "valor": custo})
            elif r in ["ESTRUTURA", "SEGURANCA", "COMADRE", "FREELANCER", "DECORACAO"]: registros_dre.append({"linha": lin, "unidade": "Estrutura & Seguranca", "tipo": "CUSTO_PAGO", "valor": custo})
            elif r in ["INGRESSOS & FLYER", "INGRESSOS, FLYER, CONVITE DOZE", "ARTE DA CAMISA", "FOTOGRAFO"]: registros_dre.append({"linha": lin, "unidade": "Marketing, Grafica & Arte", "tipo": "CUSTO_PAGO", "valor": custo})
            elif r in ["ALVARA ESPECIAL", "ALVARA NORMAL"]: registros_dre.append({"linha": lin, "unidade": "Juridico (Alvaras)", "tipo": "CUSTO_PAGO", "valor": custo})

    # Células extras
    registros_dre.append({"linha": 8, "unidade": "Bar & Alimentacao", "tipo": "RECEITA", "valor": extras["bar_especie_fisico"]})
    registros_dre.append({"linha": 6, "unidade": "Bilheteria (Pix + Cheers)", "tipo": "RECEITA", "valor": extras["cheers_retido"]})
    registros_dre.append({"linha": 7, "unidade": "Patrocinios & Permutas", "tipo": "RECEITA", "valor": extras["patrocinio_pendente"]})
    registros_dre.append({"linha": 2, "unidade": "Outras Entradas Operacionais", "tipo": "RECEITA", "valor": extras["rendimento_conta"]})
    registros_dre.append({"linha": 11, "unidade": "Bar & Alimentacao", "tipo": "A_PAGAR", "valor": extras["contas_a_pagar_coxinha"]})

    return pd.DataFrame(registros_dre)

if __name__ == "__main__":
    df_tx, extras = extrair_fluxo_caixa(ARQUIVO_ENTRADA)
    df_dre_detalhe = classificar_e_desmembrar(df_tx, extras)
    
    piv = df_dre_detalhe.pivot_table(index="unidade", columns="tipo", values="valor", aggfunc="sum", fill_value=0.0).reset_index()
    for col in ["RECEITA", "CUSTO_PAGO", "A_PAGAR"]:
        if col not in piv.columns: piv[col] = 0.0

    piv["RESULTADO_CAIXA"] = piv["RECEITA"] - piv["CUSTO_PAGO"]
    piv["RESULTADO_LIQUIDO"] = piv["RESULTADO_CAIXA"] - piv["A_PAGAR"]
    piv = piv.sort_values(by="RESULTADO_CAIXA", ascending=False)

    print("\n=== DRE GERENCIAL CONCILIADA - POLEIRO BLUES N' ROLL 2026 ===")
    print(piv[["unidade", "RECEITA", "CUSTO_PAGO", "A_PAGAR", "RESULTADO_CAIXA", "RESULTADO_LIQUIDO"]].to_string(index=False))
    print("-" * 75)
    print(f"RECEITA TOTAL:         R$ {piv['RECEITA'].sum():,.2f}")
    print(f"CUSTOS PAGOS NO FLUXO: R$ {piv['CUSTO_PAGO'].sum():,.2f}")
    print(f"CONTAS A PAGAR:        R$ {piv['A_PAGAR'].sum():,.2f}")
    print(f"LUCRO LIQUIDO FINAL:   R$ {piv['RESULTADO_LIQUIDO'].sum():,.2f}")

    with pd.ExcelWriter(ARQUIVO_SAIDA, engine="openpyxl") as writer:
        piv.to_excel(writer, sheet_name="DRE_Consolidada", index=False)
        df_dre_detalhe.to_excel(writer, sheet_name="Lancamentos_Auditados", index=False)
    print(f"\n[OK] Planilha auditada gerada com sucesso: {ARQUIVO_SAIDA}")