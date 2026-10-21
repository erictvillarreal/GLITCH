# RESULTADOS_E_posterior — EXPLORACIÓN POSTERIOR (post-hoc; no es hallazgo; no cuenta para G2)

## 1. ¿Es estable el sesgo LARGO de los índices? P(apertura→cierre > 0) por década

| serie | 1990s | 2000s | 2010s | 2020s | todo |
|---|---|---|---|---|---|
| ^GSPC | 53.6 % (n=2524) | 52.3 % (n=2514) | 54.3 % (n=2514) | 53.8 % (n=1709) | 53.5 % |
| GLD | — | 51.9 % (n=1276) | 49.9 % (n=2502) | 50.5 % (n=1701) | 50.6 % |

μ/σ diario apertura→cierre de ^GSPC (1990→2026) = +0.024 (media +2.46 pb/día, σ 1.04 %).
Ventana real MES (9:30→14:30 CT, 492 días): media -0.45 ticks/día, σ 167; μ/σ = -0.003.

Equivalencia con la tabla A de `resultados_E_valor.md` (μ/σ → WR entre decididos del bracket de MGC): 0.020 ↔ 51 %, 0.049 ↔ 52 %, 0.081 ↔ 53 %.

## 2. Valor si ese sesgo persistiera, aplicado SOLO al Combine de MES (XFA de MGC sin deriva; plan 3×364; stop 0.5; reglas verificadas)

| deriva MES | z = μ/σ | Combine hoy (P0) pasa | neto anual P0 mezcla slip{1,3} | neto anual P0 slip 3 | P3 mezcla |
|---|---|---|---|---|---|
| ninguna (alternate) | +0.000 | 21 % | $1,481 | $760 | $2,424 |
| larga en 36 años (^GSPC) | +0.024 | 22 % | $1,647 | $928 | $2,566 |
| 0.020 (≈WR 51 %) | +0.020 | 22 % | $1,644 | $928 | $2,565 |
| larga ventana 2 años MES | -0.003 | 20 % | $1,266 | $517 | $2,244 |

Lectura: es un límite superior condicional (“si el sesgo largo de 2 años o de 36 años persistiera”); no es evidencia de ventaja futura. Para actuar sobre esto haría falta pre-registrar la hipótesis ‘siempre LARGO en el Combine de MES’ y probarla en paper en sombra (G4). El sesgo largo de los índices es una prima de riesgo (explicación económica simple, G2(4)), pero un sesgo así también invierte en mercados bajistas (LARGO sube el 50.3 % de los días en 2008 y el 47.7 % en 2022, `RESULTADOS_E1.md`), y un Combine con SL/liquidación asimétricos es sensible a una caída sostenida.