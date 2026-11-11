import { useEffect, useState } from "react";

export default function App() {
  const [dre, setDre] = useState(null);
  const [auditoria, setAuditoria] = useState(null);
  const [erroApi, setErroApi] = useState(null);
  const [simInput, setSimInput] = useState({
    delta_publico_pct: 0,
    delta_ticket_pct: 0,
    delta_patrocinio_pct: 0,
  });
  const [simResult, setSimResult] = useState(null);
  const [descSuja, setDescSuja] = useState("2 camisas, 1 IF e 1 IM e 2 copos");
  const [valorSujo, setValorSujo] = useState(155.0);
  const [splitResult, setSplitResult] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch("http://localhost:8000/api/dre").then((r) => {
        if (!r.ok) throw new Error("Erro HTTP " + r.status);
        return r.json();
      }),
      fetch("http://localhost:8000/api/auditoria-ia").then((r) => {
        if (!r.ok) throw new Error("Erro HTTP " + r.status);
        return r.json();
      }),
    ])
      .then(([dadosDre, dadosAuditoria]) => {
        setDre(dadosDre);
        setAuditoria(dadosAuditoria);
        setErroApi(null);
      })
      .catch((err) => {
        setErroApi(err.message);
      });
  }, []);

  useEffect(() => {
    fetch("http://localhost:8000/api/simular-2027", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(simInput),
    })
      .then((r) => r.json())
      .then(setSimResult)
      .catch(() => {});
  }, [simInput]);

  const testarClassificador = () => {
    fetch("http://localhost:8000/api/classificar-lancamento", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ descricao: descSuja, valor: Number(valorSujo) }),
    })
      .then((r) => r.json())
      .then(setSplitResult)
      .catch(() => {});
  };

  if (erroApi) {
    return (
      <div style={{ fontFamily: "sans-serif", background: "#0a1628", color: "#fff", minHeight: "100vh", padding: 40 }}>
        <h2 style={{ color: "#f87171" }}>Quase lá! O React está funcionando, mas a API Python na porta 8000 está desligada.</h2>
        <p>Volte no VS Code, clique no primeiro terminal (python3) na barra direita do terminal e veja se o comando abaixo está rodando:</p>
        <pre style={{ background: "#112240", padding: 16, borderRadius: 8, color: "#38bdf8" }}>
          uvicorn api_finops:app --reload --port 8000
        </pre>
        <p style={{ color: "#94a3b8" }}>Detalhe técnico: {erroApi}</p>
      </div>
    );
  }

  if (!dre || !auditoria) {
    return (
      <div style={{ fontFamily: "sans-serif", background: "#0a1628", color: "#38bdf8", minHeight: "100vh", padding: 40 }}>
        <h2>Conectando ao PostgreSQL e carregando DRE do Poleiro Blues n' Roll...</h2>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: "#0a1628", color: "#f8fafc", minHeight: "100vh", padding: "32px" }}>
      <header style={{ borderBottom: "1px solid #1e293b", paddingBottom: 16, marginBottom: 24 }}>
        <span style={{ color: "#38bdf8", fontSize: 12, fontWeight: 700, letterSpacing: 1 }}>
          BTG PACTUAL FINOPS PORTFOLIO • ENTITY CONTROLLING AUTOMATION
        </span>
        <h1 style={{ margin: "6px 0 0 0", fontSize: 26 }}>
          {dre.evento} — Plataforma de Controladoria & Auditoria IA
        </h1>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 28 }}>
        <KpiCard titulo="Lançamentos no PostgreSQL" valor={dre.kpis.total_lancamentos} cor="#38bdf8" />
        <KpiCard titulo="Receita Conciliada" valor={`R$ ${dre.kpis.receita_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} cor="#4ade80" />
        <KpiCard titulo="Custos Pagos (Fluxo)" valor={`R$ ${dre.kpis.custo_pago_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} cor="#f87171" />
        <KpiCard titulo="Lucro Caixa (H10)" valor={`R$ ${dre.kpis.lucro_caixa_h10.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} cor="#60a5fa" />
        <KpiCard titulo="Lucro Líquido Final (H12)" valor={`R$ ${dre.kpis.lucro_liquido_h12.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} cor="#facc15" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 24, marginBottom: 28 }}>
        <div style={{ background: "#112240", padding: 20, borderRadius: 10, border: "1px solid #1e293b" }}>
          <h3 style={{ marginTop: 0, color: "#38bdf8" }}>1. DRE Gerencial (Query SQL ao Vivo no PostgreSQL)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", textAlign: "left", color: "#94a3b8" }}>
                <th style={{ padding: 8 }}>Unidade de Negócio</th>
                <th>Qtd</th>
                <th>Receita (R$)</th>
                <th>Custo Pago (R$)</th>
                <th>Líquido H12 (R$)</th>
              </tr>
            </thead>
            <tbody>
              {dre.dre_unidades.map((u, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: 8, fontWeight: 600 }}>{u.unidade}</td>
                  <td>{u.qtd_lancamentos}</td>
                  <td style={{ color: "#4ade80" }}>{u.receita.toFixed(2)}</td>
                  <td style={{ color: "#f87171" }}>{u.custo_pago.toFixed(2)}</td>
                  <td style={{ fontWeight: 700, color: u.resultado_liquido_h12 >= 0 ? "#38bdf8" : "#fb7185" }}>
                    {u.resultado_liquido_h12.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ background: "#112240", padding: 20, borderRadius: 10, border: "1px solid #1e293b" }}>
          <h3 style={{ marginTop: 0, color: "#facc15" }}>2. Diagnóstico do Agente de Auditoria IA</h3>
          <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 12 }}>
            Orçado Aba REAL: <b>R$ {auditoria.resumo_orcamentario.orcado_total_sem_tocha}</b> | Executado DRE:{" "}
            <b>R$ {auditoria.resumo_orcamentario.executado_total_competencia}</b> (Desvio: +{auditoria.resumo_orcamentario.desvio_liquido_pct}%)
          </p>
          {Array.isArray(auditoria.parecer_executivo_ia.insights) ? (
            auditoria.parecer_executivo_ia.insights.map((item, idx) => (
              <div key={idx} style={{ background: "#0a1628", padding: 12, borderRadius: 8, marginBottom: 10, fontSize: 13, lineHeight: 1.5 }}>
                {item}
              </div>
            ))
          ) : (
            <div style={{ background: "#0a1628", padding: 12, borderRadius: 8, fontSize: 13 }}>
              {auditoria.parecer_executivo_ia.insights}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div style={{ background: "#112240", padding: 20, borderRadius: 10, border: "1px solid #1e293b" }}>
          <h3 style={{ marginTop: 0, color: "#4ade80" }}>3. Simulador What-If — Poleiro Blues n' Roll 2027</h3>
          <SliderControl
            label={`Variação de Público (${simInput.delta_publico_pct}%)`}
            value={simInput.delta_publico_pct}
            onChange={(v) => setSimInput({ ...simInput, delta_publico_pct: v })}
          />
          <SliderControl
            label={`Variação de Ticket Médio (${simInput.delta_ticket_pct}%)`}
            value={simInput.delta_ticket_pct}
            onChange={(v) => setSimInput({ ...simInput, delta_ticket_pct: v })}
          />
          <SliderControl
            label={`Variação de Patrocínios (${simInput.delta_patrocinio_pct}%)`}
            value={simInput.delta_patrocinio_pct}
            onChange={(v) => setSimInput({ ...simInput, delta_patrocinio_pct: v })}
          />
          {simResult && simResult.projecao_2027 && (
            <div style={{ marginTop: 16, padding: 14, background: "#0a1628", borderRadius: 8 }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#4ade80" }}>
                Lucro Líquido Projetado 2027: R$ {simResult.projecao_2027.lucro_liquido_projetado.toFixed(2)}
              </div>
              <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 4 }}>
                Diferença vs. 2026 (R$ 6.002,47): R$ {simResult.projecao_2027.variacao_vs_2026_rs.toFixed(2)}
              </div>
            </div>
          )}
        </div>

        <div style={{ background: "#112240", padding: 20, borderRadius: 10, border: "1px solid #1e293b" }}>
          <h3 style={{ marginTop: 0, color: "#60a5fa" }}>4. Automação de Split Contábil (Combos Loss-Leader)</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              value={descSuja}
              onChange={(e) => setDescSuja(e.target.value)}
              style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #334155", background: "#0a1628", color: "#fff" }}
            />
            <input
              type="number"
              value={valorSujo}
              onChange={(e) => setValorSujo(e.target.value)}
              style={{ width: 90, padding: 8, borderRadius: 6, border: "1px solid #334155", background: "#0a1628", color: "#fff" }}
            />
            <button
              onClick={testarClassificador}
              style={{ padding: "8px 16px", background: "#0284c7", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}
            >
              Auditar
            </button>
          </div>
          {splitResult && (
            <pre style={{ background: "#0a1628", padding: 12, borderRadius: 8, fontSize: 12, overflowX: "auto" }}>
              {JSON.stringify(splitResult, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ titulo, valor, cor }) {
  return (
    <div style={{ background: "#112240", padding: 16, borderRadius: 10, borderTop: `3px solid ${cor}` }}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>{titulo}</div>
      <div style={{ fontSize: 22, fontWeight: 700, marginTop: 6, color: cor }}>{valor}</div>
    </div>
  );
}

function SliderControl({ label, value, onChange }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 13, marginBottom: 4 }}>{label}</div>
      <input
        type="range"
        min="-30"
        max="50"
        step="5"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%" }}
      />
    </div>
  );
}