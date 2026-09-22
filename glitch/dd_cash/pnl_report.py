"""
Reformateo a P&L tradicional del Monte Carlo YA VALIDADO de 50K-B (mismo motor/reglas de dd_cash/engine.py,
mismos datos de dd_cash/data.py, mismo seed=2026, T=20000, sin lag de transicion -- misma corrida que produjo
las cifras ya reportadas: payout p10/p50/p90 = 5,921/10,986/18,140; "Perfil de caja" fin mes 1..12).
NO es una simulacion nueva: mismo Account(50K, XFA_50K, nc_c=40, nc_x=3, samp_c=MES/G2, samp_x=MGC).
Unico cambio de codigo: el motor ahora separa fee_c_m (Combine: mensualidad + reinicio tras quiebre) de
fee_a_m (activacion al pasar) -- antes solo existia fee_m combinado. Verificado fee_c_m+fee_a_m==fee_m
(regresion exacta) y el payout p10/p50/p90 reproduce identico a lo ya reportado.
"""
import numpy as np
from dd_cash.data import build
from dd_cash.engine import Account, simulate
from core.prop_firm import TOPSTEP_50K

MASSIVE = 43.5
PI = 1.5
df = build(); mgc, mes = df.mgc.values, df.mes.values; n = len(df)
D = np.random.default_rng(2026).integers(0, n, (20000, 252))
from core.funded_account import XFA_50K
r = simulate(Account(TOPSTEP_50K, XFA_50K, 40, 3, mes, mgc), D)
pay, fc, fa = r["pay_m"], r["fee_c_m"], r["fee_a_m"]
net = pay - fc - fa - MASSIVE - PI
cum = np.cumsum(net, axis=1)

print(f"combine fee 50K (core/prop_firm.py): monthly_fee=${TOPSTEP_50K.monthly_fee} activation_fee=${TOPSTEP_50K.activation_fee}\n")
print("MENSUAL (p50 / mediana por mes, cada columna independiente):")
print("mes:      " + " ".join(f"{m+1:6d}" for m in range(12)))
print("payout:   " + " ".join(f"{v:6.0f}" for v in np.median(pay, axis=0)))
print("fee_comb: " + " ".join(f"{v:6.0f}" for v in np.median(fc, axis=0)))
print("fee_act:  " + " ".join(f"{v:6.0f}" for v in np.median(fa, axis=0)))
print("neto mes: " + " ".join(f"{v:6.0f}" for v in np.median(net, axis=0)))
print("acumulado (percentil de la trayectoria acumulada, NO cumsum de la fila 'neto mes'):")
print("  p10:    " + " ".join(f"{v:6.0f}" for v in np.percentile(cum, 10, axis=0)))
print("  p50:    " + " ".join(f"{v:6.0f}" for v in np.percentile(cum, 50, axis=0)))
print("  p90:    " + " ".join(f"{v:6.0f}" for v in np.percentile(cum, 90, axis=0)))
print("  (cumsum ingenuo de la fila 'neto mes' p50, solo para ver la diferencia): " + " ".join(f"{v:6.0f}" for v in np.cumsum(np.median(net, axis=0))))

print("\nQ1-Q4 (suma de los 3 meses p50 de cada trimestre, tal como se pidio):")
for q in range(4):
    sl = slice(q * 3, q * 3 + 3)
    py, c1, c2, ne = [np.median(x, axis=0)[sl].sum() for x in (pay, fc, fa, net)]
    print(f"  Q{q+1}: payout {py:8.0f}  fee_comb {c1:7.0f}  fee_act {c2:6.0f}  massive {3*MASSIVE:6.1f}  pi {3*PI:4.1f}  neto {ne:8.0f}")

print("\nANUAL (suma de los 12 meses p50):")
py, c1, c2, ne = [np.median(x, axis=0).sum() for x in (pay, fc, fa, net)]
print(f"  Ingresos (payout): {py:,.0f} | Egresos (fee_comb {c1:,.0f} + fee_act {c2:,.0f} + massive {12*MASSIVE:,.0f} + pi {12*PI:,.0f} = {c1+c2+12*MASSIVE+12*PI:,.0f}) | Utilidad Neta Año 1: {ne:,.0f}")
print(f"  (vs. percentil real de la trayectoria acumulada a 12 meses: p10 {np.percentile(cum[:,-1],10):,.0f} p50 {np.percentile(cum[:,-1],50):,.0f} p90 {np.percentile(cum[:,-1],90):,.0f})")

print("\nMes exacto en que la mediana de caja acumulada cruza a positivo por primera vez (recorriendo dia a dia, D=21/mes):")
med_daily = np.percentile(np.cumsum(r["take_d"] - r["fee_d"] - (MASSIVE + PI) / 21, axis=1), 50, axis=0)
first_day_pos = int(np.argmax(med_daily >= 0)) + 1 if (med_daily >= 0).any() else None
print(f"  primer dia (mediana>=0): dia {first_day_pos} -> mes {-(-first_day_pos // 21)} (mes1=dias1-21, mes2=dias22-42)")
print(f"  cumulative p50 fin de mes 1: {cum[:,0].__class__ and np.percentile(cum[:,0],50):.0f} | fin de mes 2: {np.percentile(cum[:,1],50):.0f}")

print("\nPendiente estable (mediana de 'neto mes' en meses 4-12):")
print(f"  media de las medianas mensuales (m4-m12): {np.median(net,axis=0)[3:].mean():.0f}")
print(f"  por mes (m4..m12): " + " ".join(f"{v:.0f}" for v in np.median(net, axis=0)[3:]))
