# FinOps & Entity Controlling Automation — PBNR

Plataforma Full Stack de **Automação Financeira, Conciliação Contábil e Auditoria com Inteligência Artificial**, desenvolvida para substituir controles financeiros manuais baseados em múltiplas abas de Excel por uma arquitetura escalável em **Python (Pandas + FastAPI)**, **PostgreSQL** e **React JS**.

---

## 1. Contexto de Negócio e Problema Resolvido

Em operações financeiras e de controladoria (*Entity Controlling*), o uso de planilhas complexas preenchidas manualmente gera riscos operacionais e distorções contábeis. Neste estudo de caso real (gestão financeira do evento **Poleiro Blues n' Roll 2026**, com 27 anos de história e público de 255 pessoas), o controle original em Excel possuía **14 abas interdependentes** e apresentava **5 gargalos críticos de auditoria**:

1. **Omissão Silenciosa em Fórmulas (`SUMIF`):** Uma despesa operacional de `R$ 160,00` (*Uber Tatuador*, linha 16 da aba `REAL`) foi registrada sem a tag de setor, ficando invisível no resumo orçamentário da planilha.
2. **Quebra de `COUNTIF` por Variação de Digitação:** Pacotes promocionais registrados como `"ingresso + camisa"` (9 lançamentos) e `"camisa + ingresso"` (4 lançamentos), além de variações de acentuação (`"ATRAÇÃO"` vs. `"ATRACAO"` e `"PATROCÍNIO"` vs. `"PATROCINIO"`), distorciam os somatórios automáticos do Excel.
3. **Vendas Casadas (*Loss-Leader Bundles*) sem Rateio Contábil:** Combos de ingressos com merchandising (`R$ 985,00` em 15 pacotes) estavam misturados na mesma rubrica, impedindo o cálculo real da margem líquida da bilheteria e do centro de custo de merchandising.
4. **Lançamentos Órfãos no Fechamento de Caixa:** As 4 transações finais do evento (`+R$ 5.181,00` da maquininha, `+R$ 13,00` de salgadinhos, `-R$ 2.840,00` de barris de chopp e `-R$ 160,00` de transporte) estavam sem categoria atribuída no fluxo de caixa.
5. **Assimetria entre Orçamento e Permutas (*Barter*):** Contratos de permuta com fornecedores (`R$ 600,00` em bebidas e `R$ 392,50` em gráfica) estavam zerados na aba de orçamento planejado (`REAL`), mas lançados como entradas e saídas casadas no fluxo de caixa.

---

## 2. Arquitetura da Solução

O sistema substitui a operação manual em Excel por um pipeline automatizado dividido em **4 camadas**:

* **Camada 1 — ETL & Saneamento Contábil (`etl_pbnr.py`):**
  * Extração automatizada via `openpyxl` e `pandas` com normalização Unicode (`NFD`) e padronização léxica.
  * Algoritmo de *Split Contábil* para pacotes promocionais: aloca o custo unitário de reposição ao centro de **Merchandising** ($\text{Camisa} = \text{R\$ } 29,90$ e $\text{Copo} = \text{R\$ } 5,00$) e apropria o saldo líquido à **Bilheteria**.
  * Reconciliação automática das células extra-fluxo (retido em plataforma online, patrocínios a receber, saldo em espécie no bar, rendimentos bancários e passivo a pagar).
* **Camada 2 — Persistência Relacional (`db_loader.py` + PostgreSQL):**
  * Ingestão estruturada no **PostgreSQL** via `SQLAlchemy` e `psycopg2` nas tabelas `lancamentos_auditados` ($N = 276$ registros) e `dre_consolidada` ($N = 9$ unidades de negócio).
  * Motor de consulta analítica em SQL utilizando agregações condicionais (`SUM(CASE WHEN ...)` e `GROUP BY`).
* **Camada 3 — API REST & Motor de Auditoria com IA (`api_finops.py` + FastAPI):**
  * Endpoints RESTful de baixa latência integrados ao PostgreSQL e documentados via Swagger UI (`/docs`).
  * Integração com **LLM API (Google Gemini)** e motor determinístico de *fallback* para geração automática de pareceres executivos de desvio orçamentário (*Orçado vs. Realizado*).
  * Simulador matemático *What-If* para projeção de P&L de 2027 com base em elasticidade de público, ticket médio e patrocínios.
* **Camada 4 — Dashboard Executivo (`frontend-btg/` + React JS):**
  * Interface web interativa construída em **React JS (Vite)** consumindo a API em tempo real para acompanhamento de KPIs, DRE SQL, pareceres de auditoria da IA e simulação de cenários.

---

## 3. Resultados Financeiros Conciliados (DRE Gerencial)

Abaixo está a consolidação exata gerada pela query SQL sobre os **276 lançamentos auditados** no PostgreSQL:

| Unidade de Negócio | Qtd. Lançamentos | Receita Conciliada (R$) | Custo Pago (R$) | Passivo a Pagar (R$) | Resultado Caixa H10 (R$) | Resultado Líquido H12 (R$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bilheteria (Pix + Cheers + Combos)** | 162 | `5.991,60` | `0,00` | `0,00` | `5.991,60` | `5.991,60` |
| **Patrocínios & Permutas** | 24 | `5.311,50` | `0,00` | `0,00` | `5.311,50` | `5.311,50` |
| **Bar & Alimentação** | 12 | `9.753,21` | `4.569,20` | `442,05` | `5.184,01` | `4.741,96` |
| **Outras Entradas Operacionais** | 3 | `213,95` | `0,00` | `0,00` | `213,95` | `213,95` |
| **Merchandising (Camisas & Copos)** | 52 | `2.603,40` | `2.469,50` | `0,00` | `133,90` | `133,90` |
| **Jurídico (Alvarás)** | 2 | `0,00` | `181,21` | `0,00` | `-181,21` | `-181,21` |
| **Marketing, Gráfica & Arte** | 4 | `0,00` | `1.541,50` | `0,00` | `-1.541,50` | `-1.541,50` |
| **Atrações (Bandas)** | 4 | `0,00` | `4.280,00` | `0,00` | `-4.280,00` | `-4.280,00` |
| **Estrutura & Segurança** | 13 | `0,00` | `4.387,73` | `0,00` | `-4.387,73` | `-4.387,73` |
| **TOTAL CONSOLIDADO** | **276** | **`23.873,66`** | **`17.429,14`** | **`442,05`** | **`6.444,52`** | **`6.002,47`** |

### Principais Métricas de Unit Economics e Controladoria

* **Validação da Estratégia Loss-Leader (Combos -> Consumo de Bar):** A venda promocional de combos garantiu uma cobertura de custos de merchandising de $105,4\%$ (`R$ 2.603,40` de receita atribuída contra `R$ 2.469,50` de custo) e impulsionou o público pagante a gerar um consumo médio no bar de $\text{R\$ } 38,25/\text{pessoa}$, entregando uma margem bruta de caixa de $53,2\%$ no bar (`R$ 5.184,01` de resultado de caixa).
* **Auditoria de Desvio Orçamentário (*Budget vs. Actual*):** O custo total executado por competência foi de `R$ 17.871,19` contra `R$ 16.721,96` orçados na aba `REAL` (desvio líquido de $+\text{R\$ } 1.149,23$ ou $+6,87\%$). O motor de auditoria comprova que $86,4\%$ desse desvio bruto (`R$ 992,50`) decorre da contabilização das permutas (*Eneas* `R$ 600,00` e *Blin Gráfica* `R$ 392,50`), que possuem contrapartida integral na receita de patrocínios.

---

## 4. Estrutura do Repositório

```text
pbnr-finops-automation/
├── etl_pbnr.py              # Pipeline ETL: limpeza léxica, split de combos e reconciliação da DRE
├── db_loader.py             # Carga relacional no PostgreSQL e validação via query SQL
├── api_finops.py            # API REST em FastAPI + Agente de Auditoria IA + Simulador P&L
├── requirements.txt         # Dependências Python do back-end e engenharia de dados
└── frontend-btg/            # Aplicação Front-end em React JS (Vite)
    ├── package.json
    └── src/
        ├── App.jsx          # Dashboard Executivo conectado à API FastAPI
        └── main.jsx
```

---

## 5. Como Executar o Projeto Localmente (Linux / WSL)

### 1. Pré-requisitos e Banco de Dados PostgreSQL
Certifique-se de ter o **Python 3.10+**, **Node.js 18+** e o **PostgreSQL** ativos no ambiente Linux/WSL:

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER finops_user WITH PASSWORD 'btg2027';"
sudo -u postgres psql -c "CREATE DATABASE finops_btg OWNER finops_user;"
sudo -u postgres psql -d finops_btg -c "GRANT ALL PRIVILEGES ON SCHEMA public TO finops_user;"
```

### 2. Back-end Python (ETL, Carga SQL e FastAPI)
Crie o ambiente virtual, instale as dependências e execute o pipeline de dados e a API:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Processa a planilha bruta e gera a base auditada
python3 etl_pbnr.py

# 2. Carrega os 276 lançamentos no PostgreSQL
python3 db_loader.py

# 3. Inicia o servidor da API na porta 8000
uvicorn api_finops:app --reload --port 8000
```
*A documentação interativa da API (Swagger UI) ficará disponível em `http://localhost:8000/docs`.*

### 3. Front-end Executivo (React JS)
Em um segundo terminal, instale os pacotes e inicie o servidor do Vite:

```bash
cd frontend-btg
npm install
npm run dev
```
*O Dashboard Executivo ficará disponível em `http://localhost:5173`.*

---

## 6. Autor

**Guilherme Zarattini Figueira**  
Graduando em Ciência da Computação — Universidade Federal de Ouro Preto (UFOP)  
Presidente e Gestor Financeiro — República Poleiro dos Anjos