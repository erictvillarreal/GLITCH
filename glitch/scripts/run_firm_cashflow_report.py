"""Reporte completo del motor de caja por firma (SANDBOX / R&D, offline). Salida: dd_cash/firms_cashflow_report.txt y dd_cash/firms_cashflow_summary.csv.
Para cada firma y cada politica de EVALUACION (G2 tal cual = lo que corre hoy en Topstep; TP-al-target = propuesta) se reportan dos politicas de FONDEADA:
  A) optima del grid sin restricciones (riesgo maximo diario: stop = el piso) -> es la que mas probablemente dispare alertas de conducta;
  B) conservadora: riesgo diario <= 50% de la distancia al piso y bracket <= $400 -> compatible con un perfil de conducta mas defendible.
Seleccion del grid con semilla 1000 (n=2500); evaluacion final con otra semilla (n=30000); robustez H1/H2 con tercera semilla. Una sola historia de 515 dias."""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.g2_real_rules_scan import build_tables
from dd_cash.engine_firms import firm_specs, run_firm, summarize, OPS_MONTHLY, E_COMM, F_COMM

def ops_for(name, api_bulenox=100.0):
    if "Topstep" in name: return OPS_MONTHLY["Topstep"]
    if "Bulenox" in name: return 43.5 + 1.5 + api_bulenox
    return OPS_MONTHLY["Tradeify"]

def with_comm(spec, mult):
    E, F, PF, k = spec; E = E.copy(); F = F.copy(); E[E_COMM] *= mult; F[F_COMM] *= mult
    return E, F, PF, k

def pick(T, name, g2, constrained):
    best = None
    for g in (100, 150, 250, 400, 600):
        for rho in (0.2, 0.35, 0.5, 0.75, 1.0):
            for tp in (20, 40, 80):
                if constrained and (rho > 0.5 or g > 400): continue
                spec = firm_specs(g_f=g, rho=rho, tp_f=tp, g2=g2)[name]
                r = summarize(name, *run_firm(T, name, spec, n_paths=2500, seed0=1000), ops_for(name))
                if best is None or r["net_mes_medio"] > best[0]: best = (r["net_mes_medio"], g, rho, tp)
    return best[1:]

def line(r):
    return (f"neto/mes(m3-12): media ${r['net_mes_medio']:,.0f} mediana ${r['net_mes_mediano']:,.0f} | acum12m p10/p50/p90/media ${r['acum12_p10']:,.0f}/${r['acum12_p50']:,.0f}/${r['acum12_p90']:,.0f}/${r['acum12_medio']:,.0f} "
            f"| P(<0)={r['p_neg']:.2f} | colchon p95/p99 ${r['colchon_p95']:,.0f}/${r['colchon_p99']:,.0f} | mes equilibrio (mediana)={r['mes_equilibrio_mediana'] or 'no llega'} "
            f"| compras/año={r['evals']:.1f} fondeadas={r['fondeadas']:.1f} pagos={r['pagos']:.1f} | payout anual medio ${r['payout_anual_medio']:,.0f} fees ${r['fees_anual']:,.0f} ops ${r['ops_anual']:,.0f}")

if __name__ == "__main__":
    T = build_tables(); nd = len(T[0]); allidx = np.arange(nd); h1, h2 = np.arange(nd // 2), np.arange(nd // 2, nd)
    rows = []; out_lines = []
    def P(s=""):
        print(s); out_lines.append(s)
    for g2 in (True, False):
        P("=" * 170); P("EVALUACION: " + ("G2 TAL CUAL (nc=40, TP40, SL100) = lo que corre hoy en Topstep" if g2 else "TP-AL-TARGET (propuesta de investigacion, stop propio)")); P("=" * 170)
        for name in firm_specs(g2=g2):
            for constrained in (False, True):
                if "Fast Track" in name and g2: continue            # Fast Track no tiene evaluacion
                g, rho, tp = pick(T, name, g2, constrained)
                spec = firm_specs(g_f=g, rho=rho, tp_f=tp, g2=g2)[name]
                r = summarize(name, *run_firm(T, name, spec, n_paths=30000, seed0=50000), ops_for(name))
                a = summarize(name, *run_firm(T, name, spec, n_paths=10000, seed0=90000, idx=h1), ops_for(name))
                b = summarize(name, *run_firm(T, name, spec, n_paths=10000, seed0=90000, idx=h2), ops_for(name))
                s15 = summarize(name, *run_firm(T, name, with_comm(spec, 1.5), n_paths=15000, seed0=70000), ops_for(name))
                h = summarize(name, *run_firm(T, name, spec, n_paths=15000, seed0=71000), ops_for(name))
                tag = "B conservadora" if constrained else "A optima sin restricciones"
                P(f"\n{name} | fondeada {tag}: G_f=${g}, rho={rho}, TP={tp}\n   {line(r)}\n   pass 1a evaluacion={r['pass_primera']:.3f} | H1 ${a['net_mes_medio']:,.0f}/mes P(<0)={a['p_neg']:.2f} | H2 ${b['net_mes_medio']:,.0f}/mes P(<0)={b['p_neg']:.2f}"
                  f" | comisiones +50%: ${s15['net_mes_medio']:,.0f}/mes | payouts -20% (demora/rechazos): ${(h['net_mes_medio'] - 0.2 * h['payout_anual_medio'] / 12):,.0f}/mes")
                P("   neto mensual p50 por mes 1..12: " + " ".join(f"{v:6.0f}" for v in r["net_mensual_p50"]) + "\n   neto mensual MEDIO por mes 1..12: " + " ".join(f"{v:6.0f}" for v in r["net_mensual_medio"]))
                rows.append(dict(eval_policy="G2 tal cual" if g2 else "TP-al-target", firm=name, fondeada=tag, g_f=g, rho=rho, tp=tp, net_mes_medio=round(r["net_mes_medio"]), net_mes_mediano=round(r["net_mes_mediano"]),
                                 acum12_p10=round(r["acum12_p10"]), acum12_p50=round(r["acum12_p50"]), acum12_p90=round(r["acum12_p90"]), p_neg=round(r["p_neg"], 3),
                                 colchon_p95=round(r["colchon_p95"]), colchon_p99=round(r["colchon_p99"]), mes_equilibrio=r["mes_equilibrio_mediana"], compras_anio=round(r["evals"], 1),
                                 fondeadas=round(r["fondeadas"], 1), pagos=round(r["pagos"], 1), payout_anual=round(r["payout_anual_medio"]), fees_anual=round(r["fees_anual"]),
                                 pass_primera=round(r["pass_primera"], 3), h1_net_mes=round(a["net_mes_medio"]), h2_net_mes=round(b["net_mes_medio"]), comm150_net_mes=round(s15["net_mes_medio"])))
    # sensibilidad: costo de API de Bulenox ($100/mes) vs $0 y vs Topstep ($14.5)
    P("\n" + "=" * 170 + "\nSENSIBILIDAD AL COSTO DE API (politica B, evaluacion TP-al-target)\n" + "=" * 170)
    for name in ("Bulenox Momentum 50K (Opcion 2)", "Bulenox Qualification Opcion 2 50K + Master"):
        g, rho, tp = pick(T, name, False, True)
        spec = firm_specs(g_f=g, rho=rho, tp_f=tp)[name]
        for api in (100.0, 14.5, 0.0):
            r = summarize(name, *run_firm(T, name, spec, n_paths=20000, seed0=50000), ops_for(name, api))
            P(f"  {name} API ${api:5.1f}/mes: neto/mes(m3-12) ${r['net_mes_medio']:,.0f} P(<0)={r['p_neg']:.2f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "firms_cashflow_report.txt"), "w").write("\n".join(out_lines))
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "firms_cashflow_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
