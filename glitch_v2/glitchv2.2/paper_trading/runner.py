"""
Glitch — Paper Trading Runner
================================
Orquesta: datos -> señal ORB -> Telegram -> SQLite -> stats en vivo.

FEED: ProjectX/TopstepX (brokers/projectx.py, ya existente en el repo).
Cubre paper trading (`--mode paper`) Y ejecucion real (`--mode live`).

>>> REGLA DE CUMPLIMIENTO DE TOPSTEP (NO NEGOCIABLE) <<<
"Toda actividad de trading debe originarse desde tu dispositivo personal.
El uso de VPS, VPNs y servidores remotos esta prohibido por los Terminos
de Uso de Topstep." Esto aplica UNICAMENTE cuando hay dinero/cuenta real
de por medio (`--mode live`, DRY_RUN=false). El modo paper (`--mode paper`)
NO envia ordenes a Topstep — no ejecuta nada en su plataforma, solo lee
datos de mercado y simula — por eso es seguro correrlo en Railway u otro
cloud. `--mode live` exige la bandera explicita `--confirm-personal-device`
como candado minimo (no puede detectar VPS de verdad, pero obliga a que
quien lo activa lo haga a conciencia).

USO:
    # Paper trading 24/7 en Railway — sin riesgo de cumplimiento
    python -m paper_trading.runner --mode paper --loop --poll-seconds 60

    # Ejecucion real — SOLO desde tu Mac/Raspberry Pi personal
    python -m paper_trading.runner --mode live --loop --poll-seconds 60 \\
        --account-id 12345 --confirm-personal-device
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from datetime import datetime, timezone
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.orb import ORBConfig, generate_orb_signals
from data.loader import INSTRUMENT_SPECS
from paper_trading import store, telegram_notify
from simulation.grid_search import minimum_sample_size
from brokers.projectx import ProjectXClient, ProjectXCredentials

SYMBOL = "MES"
CONTRACTS = 10           # combine phase (maximizar EV/dia). Fase XFA usa 5 (ver core/funded_account.py)
PT_MULT = 3.0             # target = entry +/- PT_MULT * ATR(volatility_window)
SL_MULT = 1.5
STRATEGY_NAME = "ORB_15m_v1"

_client: ProjectXClient | None = None
_contract_id: str | None = None


def _get_client() -> ProjectXClient:
    global _client, _contract_id
    if _client is None:
        creds = ProjectXCredentials.from_file(".projectx_creds.json")
        _client = ProjectXClient(creds, verbose=False)
        _client.authenticate()
        _contract_id = _client.find_mes_contract()["id"]
    return _client


def _bars_to_df(raw_bars: list[dict]) -> pd.DataFrame:
    """
    Convierte la respuesta de ProjectX get_bars() al esquema estandar del repo
    (open, high, low, close, volume; DatetimeIndex UTC ascendente).
    El formato exacto de las keys de ProjectX no esta 100% documentado en
    este repo -- si esto falla, imprime las keys reales del primer bar para
    ajustar el mapeo (ver except abajo).
    """
    if not raw_bars:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    try:
        df = pd.DataFrame(raw_bars)
        ts_col = next(c for c in df.columns if c.lower() in ("t", "timestamp", "time", "startedat", "started_at"))
        df["ts"] = pd.to_datetime(df[ts_col], utc=True)
        col_map = {c.lower(): c for c in df.columns}
        rename = {}
        for want, aliases in [("open", ["o", "open"]), ("high", ["h", "high"]),
                               ("low", ["l", "low"]), ("close", ["c", "close"]),
                               ("volume", ["v", "volume"])]:
            for a in aliases:
                if a in col_map:
                    rename[col_map[a]] = want
                    break
        df = df.rename(columns=rename).set_index("ts").sort_index()
        return df[["open", "high", "low", "close", "volume"]]
    except (StopIteration, KeyError) as e:
        raise RuntimeError(
            f"No pude mapear el formato de bars de ProjectX. Keys recibidas: "
            f"{list(raw_bars[0].keys())}. Ajusta _bars_to_df() en runner.py. Error: {e}"
        )


def get_latest_bars(lookback_bars: int = 150) -> pd.DataFrame:
    """Trae las ultimas N barras de 1min de MES via ProjectX (feed real, no delayed)."""
    client = _get_client()
    raw = client.get_bars(_contract_id, bar_type=1, bar_size=1, count=lookback_bars, live=True)
    return _bars_to_df(raw)


def check_open_signals(latest_bars: pd.DataFrame):
    """Revisa señales abiertas contra el precio actual: hit stop/target/timeout."""
    open_df = store.open_signals()
    if open_df.empty:
        return
    last = latest_bars.iloc[-1]
    point_value = INSTRUMENT_SPECS[SYMBOL]["point_value_usd"]

    for _, row in open_df.iterrows():
        hit_target = (row.side == 1 and last["high"] >= row.target_price) or \
                     (row.side == -1 and last["low"] <= row.target_price)
        hit_stop = (row.side == 1 and last["low"] <= row.stop_price) or \
                   (row.side == -1 and last["high"] >= row.stop_price)

        if hit_target and not hit_stop:
            pnl = store.close_signal(row.id, "win", row.target_price, point_value)
            telegram_notify.notify_close(row.telegram_msg_id, row.strategy, row.symbol, "win", pnl)
        elif hit_stop:
            pnl = store.close_signal(row.id, "loss", row.stop_price, point_value)
            telegram_notify.notify_close(row.telegram_msg_id, row.strategy, row.symbol, "loss", pnl)
        # si no toco ninguno, se queda abierta


def check_new_signals(bars: pd.DataFrame):
    """Corre el generador de señales ORB sobre las barras del dia y registra las nuevas."""
    cfg = ORBConfig(or_minutes=15, confirm_close=True)
    sig = generate_orb_signals(bars, cfg)
    if sig.empty:
        return

    today = datetime.now(timezone.utc).date().isoformat()
    already = store.open_signals()
    already_today = already[already.session_date == today] if not already.empty else already

    for _, s in sig.iterrows():
        # evitar duplicar la misma señal (mismo lado, mismo dia)
        if not already_today.empty and (already_today.side == s.side).any():
            continue

        entry_bar = bars.iloc[s.entry_idx]
        entry_price = float(entry_bar["close"])
        # ATR aproximado con el mismo criterio que triple_barrier (rolling TR)
        atr = float((bars["high"] - bars["low"]).rolling(100, min_periods=1).mean().iloc[s.entry_idx])
        stop = entry_price - s.side * SL_MULT * atr
        target = entry_price + s.side * PT_MULT * atr

        new_sig = store.Signal(
            strategy=STRATEGY_NAME, symbol=SYMBOL, side=int(s.side),
            entry_price=entry_price, stop_price=stop, target_price=target,
            contracts=CONTRACTS, session_date=today,
        )
        sig_id = store.log_signal(new_sig)
        msg_id = telegram_notify.notify_signal(
            STRATEGY_NAME, SYMBOL, int(s.side), entry_price, stop, target, CONTRACTS
        )
        store.set_telegram_msg_id(sig_id, msg_id)


def tick():
    bars = get_latest_bars()
    check_open_signals(bars)
    check_new_signals(bars)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["paper", "live"], default="paper",
                     help="paper = solo lectura de datos + simulacion (seguro en cloud). "
                          "live = envia ordenes reales -- requiere --confirm-personal-device.")
    ap.add_argument("--account-id", type=int, help="Requerido para --mode live")
    ap.add_argument("--confirm-personal-device", action="store_true",
                     help="Confirmas explicitamente que este proceso corre en TU dispositivo "
                          "personal (no VPS/cloud), cumpliendo los Terminos de Uso de Topstep.")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--poll-seconds", type=int, default=60)
    ap.add_argument("--digest", action="store_true", help="Mandar resumen diario y salir")
    args = ap.parse_args()

    if args.mode == "live" and not args.confirm_personal_device:
        print(
            "[glitch] ABORTADO: --mode live requiere --confirm-personal-device.\n"
            "Los Terminos de Uso de Topstep prohiben correr automatizacion de trading "
            "real desde un VPS/servidor remoto. Si estas en tu Mac/Raspberry Pi personal, "
            "vuelve a correr agregando --confirm-personal-device."
        )
        sys.exit(1)

    if args.digest:
        stats = store.running_stats(STRATEGY_NAME)
        target_n = minimum_sample_size(target_pass_rate=0.5, margin=0.03)  # referencia; ajustar segun objetivo real
        telegram_notify.notify_daily_digest(stats, target_n)
        return

    if args.loop:
        while True:
            try:
                tick()
            except NotImplementedError as e:
                print(f"[glitch] {e}")
                break
            except Exception as e:
                print(f"[glitch] error en tick(): {e}")
            time.sleep(args.poll_seconds)
    else:
        tick()


if __name__ == "__main__":
    main()
