# resultados_G1b — distribución de slippage de entrada (ticks; + = adverso)

Fuente: 2 observaciones de Eric (19-oct SHORT, 20-oct LONG; fuente: mensajes [OPEN] y TopstepX).

- N = 2; valores: +1.00, +3.00; media +2.00; desvío 1.41; IC95 bootstrap de la media [+1.00, +3.00]; P(s > 1) = 0.50; P(s ≥ 2) = 0.50.
- **Potencia:** con N = 2 el IC no significa nada (el bootstrap de 2 puntos es degenerado). Para estimar la media con EE ≈ 0.4 tick hacen falta ≈ 25–30 sesiones si σ ≈ 2 ticks (**supuesto**); para separar 1 de 2 ticks de media, ≈ 30; para P(s > 1) con ±17 pp, ≈ 30. **Sin potencia hoy.**
- El historial de operaciones de TopstepX no basta por sí solo: trae el fill pero no la referencia. Necesita: (a) los mensajes [OPEN] de Telegram (referencia) o (b) el parche C3 (`exec.ref_price`, `exec.fill_price`, `exec.t_*`).
- Los fills de MES nc 10 y MEStest son útiles para separar **sistemático vs aleatorio**: el sistemático debería crecer con el tamaño (nc 10 vs 40) y el aleatorio no.