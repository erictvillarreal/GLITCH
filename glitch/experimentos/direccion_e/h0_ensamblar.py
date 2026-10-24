"""Parte H, H0: ensambla resultados_H0.md = parte 1 + parte 2 + «Dónde NO hay probabilidades».   python h0_ensamblar.py"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
p1 = open(os.path.join(HERE, "resultados_H0_parte1.md"), encoding="utf-8").read()
p2 = open(os.path.join(HERE, "resultados_H0_parte2.md"), encoding="utf-8").read().split("\n", 1)[1]
no = '''

## Dónde NO hay probabilidades (DESCONOCIDO): por qué, qué dato lo resolvería, costo y fecha estimada

| cantidad | por qué no se sabe hoy | qué dato lo resolvería | costo de obtenerlo | fecha estimada |
|---|---|---|---|---|
| **WR real de la estrategia (MES y MGC)** | 8 trades reales de MES (7 decididos) y 1 decidido en MGC Practice; el histórico de 2 años es un solo camino de precios (IC95 de WR_dec en MGC ±6.6 pp) | ≥ 620 trades decididos para distinguir 55 % de 50 %; ≥ 2,306 para 47.4 % de 50 % (binomial exacta, α 5 %, potencia 80 %) | tiempo: MES ≈ 1 decidido/día ⇒ **2.5 años** (620) o **≈ 9 años** (2,306); MGC (≈ 44 % decididos) el doble | **no hay forma rápida**; se decide con cotas (equilibrio 48.6 %), no con el WR medido |
| **Slippage de entrada: media, σ y parte sistemática vs aleatoria** | N = 2 (+1, +3 ticks) | C3 (parche listo) + exportación de fills de TopstepX cruzada con los `[OPEN]` | desplegar C3 (revisión humana) y 30–60 sesiones | ≈ **6–12 semanas** tras desplegar (hacia mediados de enero si se despliega el 27-oct); la exportación de TopstepX puede dar una primera lectura en **días** |
| **Slippage de salida y sobreimpulso de la liquidación por MLL** | ningún precio de salida real en el repo (el caso del 19-oct no está) | historial de operaciones de TopstepX (salida y hora) + `exec_exit` de C3 | 1–2 h de exportación | **días** |
| **TP: fills parciales o espera en cola** | sin detalle de fills | misma exportación | — | días |
| **Latencia real señal → orden → fill** | sin logs/timestamps del Pi en esta sesión | `~/glitch-logs/pi_executor.log` (19–23 oct) y C3 | minutos | días |
| **¿El Combine tiene DLL? ¿restricciones de noticias Tier 1 en el Combine?** | el artículo leído es de la XFA | ticket a Topstep o pantalla de la cuenta en TopstepX | 1 ticket | días |
| **Umbrales de RTP / «compras excesivas» / copia de la estrategia en varias cuentas** | no publicados | ticket a Topstep | 1 ticket | días–semanas |
| **Semántica de los brackets nativos (ticks desde el fill o desde otro precio; modo OCO elegible; efecto del rechazo con `errorCode 2`)** | la doc de ProjectX no lo dice | ensayo en Practice (una sesión) | bajo | **1 día** de Practice |
| **Régimen futuro de volatilidad del oro / FLATTEN** | no estacionario (FLATTEN 90 % → 28 % por bloques) | monitoreo de la fracción FLATTEN por bloque; no se puede «medir» el futuro | — | continuo |
| **Correlación entre resultados de cuentas / de dos productos** | solo existe la correlación de retornos de la ventana (MES–MGC 0.17, MES–MNQ 0.97) | un segundo producto en Practice ≥ 60 sesiones | medio | ≈ 3 meses |
| **Fiabilidad operativa de la cadena (Railway → Gist → Pi)** | un incidente documentado, sin tasa | registro de fallos con fecha desde el 21-oct | — | ≈ 3 meses |
| **P(activar la XFA tras pasar)** | decisión humana | — | — | SUPUESTO = 100 % |
| **Cierres de CME (26/27-nov, 24-dic); PPI, ISM, ventas minoristas** | no consultados en fuente primaria (las fuentes de terceros discrepan) | calendario de CME y de cada agencia | minutos | días |
| **Costos operativos de $714/año** | cifra heredada de la Parte D; no se verificó qué incluye | factura de Railway/datos | minutos | días |
'''
open(os.path.join(HERE, "resultados_H0.md"), "w", encoding="utf-8").write(p1 + "\n\n" + p2 + no)
print(len(p1), len(p2))
