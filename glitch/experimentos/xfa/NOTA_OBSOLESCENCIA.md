# Nota de obsolescencia — `CEREBRO2_G2_VS_MGC_SUMMARY.md` (6-sep-2026) — 20-oct-2026

**Recomendación: marcar ese documento como OBSOLETO y no usarlo como evidencia.** No lo modifiqué (vive en las ramas `dd/*`, `research/*` y `cerebro2-dev`, fuera de este encargo); basta añadirle un banner de una línea apuntando a este archivo.

Cifras del documento y por qué quedaron superadas:

| cifra del 6-sep | problema | evidencia actual |
|---|---|---|
| **81.4 %** de pase del Combine | invalidada después (convención de 100 barras / sin flatten, sin consistencia oficial ni liquidación en tiempo real) | pase por intento 17–29 % según slippage (Parte A / C1) |
| **46.9 %** (P de pago de la XFA) | XFA 150K sin liquidación en tiempo real, con el piso trabado en +MLL y tope de $5,000 | 50K: P(≥1 pago) 33–36 % con reglas verificadas |
| **$2,169** (neto anual) | convención previa (haircut, sin slippage) | rango anual $0.5k–$2.7k (`REPORTE_D.md`) |
| **$31,257** (mediana de caja de la cadena larga) | cuenta **150K** nc 6, sin liquidación en tiempo real, tope de pago por tamaño inexistente (se corrigió el 24-sep), y **serie MGC con barras de dos contratos mezcladas** (`EVIDENCIA_CEREBRO2.md` §1.1) | no comparable con la 50K |

Fuentes de la corrección: `GLITCH_RESEARCH_LOG.md` (24/25-sep, 7-oct), `core/funded_account.py` (rama de investigación), `RULEBOOK_XFA.md` (reglas leídas 20-oct), `INVENTARIO_XFA.md` (C1–C4).
