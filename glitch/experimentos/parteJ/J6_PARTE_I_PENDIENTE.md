# J6 — Parte I: neto anual de planes angostos — **NO REALIZADO**

Lunes 26-oct-2026. **No tengo el encargo de la Parte I** (ni en el repo, ni en los documentos de esta conversación, ni en `auditoria_experimentos/`), y «planes angostos» no se define en J. No quiero adivinar y entregar un número con otra definición: el protocolo de este proyecto pide fuentes primarias y no inventar cifras.

**Lo que necesito de Eric (una de dos):**
1. el texto de la Parte I (o la definición de «plan angosto» y los escenarios que debe comparar), o
2. confirmar la interpretación más probable: *planes con brackets más angostos que 364/364* (p. ej. SL = TP ∈ {100, 150, 182, 250}) en la XFA de MGC con 3 micros, comparados por neto anual de la cadena con la misma metodología de J3/J5.

**Lo que ya existe y sirve de base:** `direccion_e/h6_geometria.py` (razón TP:SL distinta de 1:1: ninguna es mejor que 364/364 con z* base; diferencias < 0.015 en z*, sin bootstrap), `parteJ/j8_primer_dia_xfa.py` (vidas de la XFA con IC y diferencias pareadas) y `parteJ/j5_intervalo_206.py` (cadena anual con IC). Con la definición, J6 es una corrida de ≈ 30 minutos.

**Advertencia metodológica ya conocida:** con SL = TP simétrico y deriva ≈ 0, estrechar el bracket no crea ventaja; cambia la composición (más sesiones decididas, menos FLATTEN) y, en la XFA, los FLATTEN aportan la mitad de los días ganadores ≥ $150 (H3): «más decididas» tendió a **acortar** la vida de la cuenta, no a acelerar el cobro (REPORTE_H §2.2).
