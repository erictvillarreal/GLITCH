import pandas as pd
import yfinance as yf
"""
GLITCH — Combo2d MNQ Scheduler
Estrategia: mean-reversion dia-a-dia con doble confirmacion MES+MNQ
Señal: -sign(ret_prev) cuando sign(ret_2d) != sign(ret_prev) en AMBOS instrumentos
Entrada: apertura RTH (9:30 CT)
Salida: via triple-barrier ATR (pt=2.5x, sl=1.5x) o fin de sesion (14:30 CT)
Railway Cron: 25 14 * * 1-5 (9:25 AM CT L-V)
"""
import os, sys, logging, time, datetime as dt_module
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from massive import RESTClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scheduler.telegram_bot import send
from strategies.combo2d import decide_side
from simulation.triple_barrier import compute_atr as _shared_compute_atr
from execution.contracts import MASSIVE_API_KEY, get_front_month, check_expiry_alerts
from execution.gist_store import load_log as _gist_load_log, save_log as _gist_save_log

CT = ZoneInfo("America/Chicago")
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO,
    format="%(asctime)s CT [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("combo2d")

# ── Config ────────────────────────────────────────────────────────────────────
DRY_RUN       = os.getenv("DRY_RUN", "true").lower() == "true"
NC            = int(os.getenv("NC", "6"))          # contratos MNQ
MNQ_POINT     = 2.0                                 # $2 por punto MNQ
ATR_PT_MULT   = 2.5                                 # TP = 2.5 * ATR
ATR_SL_MULT   = 1.5                                 # SL = 1.5 * ATR
ATR_WINDOW    = 20                                  # barras para ATR
LOG_FILE      = "combo2d_log.json"  # nombre del archivo DENTRO del gist compartido -- ver execution/gist_store.py
POLL_INTERVAL = 60  # segundos entre polls

# ── Helpers ───────────────────────────────────────────────────────────────────
def ct_now(): return datetime.now(CT)

# REFACTOR (27-ago-2026): load_log()/save_log() ya NO leen/escriben el
# filesystem local -- los servicios "Cron Schedule" de Railway no tienen
# volumen persistente (confirmado en el dashboard), asi que un archivo
# local se reseteaba en CADA corrida. Delegan a execution/gist_store.py
# (persistencia via GitHub Gist) -- misma firma, mismos call sites, solo
# cambia el mecanismo de I/O. Ver GLITCH_RESEARCH_LOG.md.
def load_log():
    return _gist_load_log(LOG_FILE)

def save_log(l):
    _gist_save_log(LOG_FILE, l)

def is_trading_day():
    now = ct_now()
    if now.weekday() >= 5: return False
    holidays = {
        (2026,1,1),(2026,1,19),(2026,2,16),(2026,4,3),
        (2026,5,25),(2026,7,3),(2026,9,7),(2026,11,26),(2026,12,25)
    }
    return (now.year, now.month, now.day) not in holidays

# REFACTOR (25-ago-2026): resolucion de front-month movida a
# execution/contracts.py -- unica fuente de verdad, compartida con
# scheduler/geometry_scheduler.py. Ya no hay dict hardcodeado ni logica
# duplicada aqui.
_front_month_cache: dict[str, tuple[str, str]] = {}  # product -> (ticker, last_trade_date)

def fetch_daily(product, n_days=15):
    """Descarga n_days de datos diarios via Massive."""
    try:
        ticker = get_front_month(product, _front_month_cache)
        client = RESTClient(MASSIVE_API_KEY)
        end   = date.today().isoformat()
        start = (date.today() - timedelta(days=n_days*2)).isoformat()
        bars  = list(client.list_futures_aggregates(
            ticker,
            window_start_gte=start,
            window_start_lte=end,
            limit=200, sort="asc",
        ))
        if len(bars) < 3: return None
        rows = [{"open": b.open, "close": b.close,
                 "ret": (b.close-b.open)/b.open if b.open else 0}
                for b in bars]
        return rows  # lista de dicts ordenada por fecha asc
    except Exception as e:
        log.error(f"fetch_daily {product}: {e}")
        return None

def fetch_intraday(ticker):
    """Descarga barras de hoy en 1min para calcular ATR y precio actual."""
    try:
        d = yf.Ticker(ticker).history(period="5d", interval="1m", prepost=False)
        if d.empty: return None
        d = d.reset_index()
        d.columns = [c.lower() for c in d.columns]
        tcol = [c for c in d.columns if 'date' in c or 'time' in c][0]
        d['dt']  = pd.to_datetime(d[tcol], utc=True).dt.tz_convert(CT)
        d['t']   = d['dt'].dt.hour*60 + d['dt'].dt.minute
        d['day'] = d['dt'].dt.date
        today = date.today()
        rth = d[(d['day']==today) & (d['t']>=9*60+30) & (d['t']<=14*60+30)].copy()
        return rth.reset_index(drop=True)
    except Exception as e:
        log.error(f"fetch_intraday {ticker}: {e}")
        return None

def compute_atr(bars, window=20):
    """
    ATR simple sobre barras recientes.
    REFACTOR (25-ago-2026): delega a simulation.triple_barrier.compute_atr
    (unica fuente de verdad) en vez de reimplementar el true-range aqui.
    atr_series[-1] es exactamente equivalente a la formula original
    (mean(tr[-window:])), porque rolling(window, min_periods=1).mean() en
    la ultima posicion promedia las mismas ultimas `window` barras.
    """
    if bars is None or len(bars) < 3: return None
    h = bars['high'].values; l = bars['low'].values; c = bars['close'].values
    atr_series = _shared_compute_atr(h, l, c, window)
    return float(atr_series[-1])

def compute_signal():
    """
    Genera la señal combo_2d usando Yahoo datos diarios.
    Retorna: (side, reason) donde side = 1 (long) / -1 (short) / 0 (no trade)

    REFACTOR (25-ago-2026): la decision (dado ret_prev/ret_2d de MES y MNQ)
    delega a strategies.combo2d.decide_side() -- unica fuente de verdad,
    compartida con el backtest (ver tests/test_combo2d_parity.py).
    """
    mes = fetch_daily("MES", n_days=15)
    mnq = fetch_daily("MNQ", n_days=15)

    if mes is None or mnq is None:
        return 0, "datos_insuficientes"
    if len(mes) < 3 or len(mnq) < 3:
        return 0, "historia_insuficiente"

    # Massive entrega solo barras cerradas — la ultima fila es T-1 (ayer)
    # [-1]=T-1 (ayer, completo), [-2]=T-2 (anteayer, completo)
    mes_ret_prev = mes[-1]["ret"]  # T-1
    mes_ret_2d   = mes[-2]["ret"]  # T-2
    mnq_ret_prev = mnq[-1]["ret"]
    mnq_ret_2d   = mnq[-2]["ret"]

    log.info(f"MES: ret_prev={mes_ret_prev:.4f} ret_2d={mes_ret_2d:.4f}")
    log.info(f"MNQ: ret_prev={mnq_ret_prev:.4f} ret_2d={mnq_ret_2d:.4f}")

    return decide_side(mes_ret_prev, mes_ret_2d, mnq_ret_prev, mnq_ret_2d)

def run():
    import pandas as pd  # import aqui para no requerir en el top si falla
    log.info("=" * 60)
    log.info("GLITCH — Combo2d MNQ Scheduler")
    log.info(f"DRY_RUN={DRY_RUN}  NC={NC}")
    log.info("=" * 60)

    if not is_trading_day():
        log.info("No es dia de trading — saliendo")
        return

    now = ct_now()
    today_str = str(date.today())
    paper_log = load_log()

    # Espera hasta 9:25 CT si arrancamos antes
    while ct_now().hour * 60 + ct_now().minute < 9*60+25:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura...")
        time.sleep(30)

    # ── 1. Genera señal (datos del día anterior, disponibles antes de apertura) ──
    log.info("Calculando señal combo_2d...")
    side, reason = compute_signal()
    direction_str = {1: "LONG", -1: "SHORT", 0: "NO_TRADE"}[side]
    log.info(f"Señal: {direction_str} | {reason}")
    log.info(f"Contratos en uso: {_front_month_cache}")
    check_expiry_alerts(_front_month_cache, send, "COMBO2D")

    if side == 0:
        msg = f"""GLITCH - COMBO2D
STATUS: NO SIGNAL
REASON: {reason}"""
        send(msg)
        paper_log.append({"date": today_str, "signal": False, "pnl": 0, "note": reason})
        save_log(paper_log)
        log.info("Sin señal — saliendo")
        return

    # ── 2. Espera apertura 9:30 CT ─────────────────────────────────────────────
    while ct_now().hour * 60 + ct_now().minute < 9*60+30:
        log.info(f"[{ct_now().strftime('%H:%M')} CT] Esperando apertura RTH...")
        time.sleep(15)

    # ── 3. Obtiene precio de entrada y ATR ─────────────────────────────────────
    log.info("Obteniendo precio de apertura MNQ...")
    entry_bars = None
    for attempt in range(8):
        entry_bars = fetch_intraday("MNQ=F")
        if entry_bars is not None and len(entry_bars) >= 1:
            break
        log.info(f"  Esperando datos MNQ ({attempt+1}/8)...")
        time.sleep(30)

    if entry_bars is None or entry_bars.empty:
        msg = """GLITCH - COMBO2D
STATUS: ERROR
ERROR: No MNQ data available for entry"""
        send(msg)
        paper_log.append({"date": today_str, "signal": True, "side": side,
                          "pnl": 0, "note": "no_data_entry"})
        save_log(paper_log)
        return

    entry_price = float(entry_bars.iloc[-1]['close'])
    atr = compute_atr(entry_bars, ATR_WINDOW) or 5.0  # fallback 5 puntos
    tp_pts = atr * ATR_PT_MULT
    sl_pts = atr * ATR_SL_MULT
    tp_price = entry_price + side * tp_pts
    sl_price = entry_price - side * sl_pts

    log.info(f"Entrada: {direction_str} @ {entry_price:.2f}")
    log.info(f"ATR={atr:.2f}  TP={tp_price:.2f} (+{tp_pts:.2f}pts)  SL={sl_price:.2f} (-{sl_pts:.2f}pts)")

    msg = (f"GLITCH DETECTED - COMBO2D\n"
           f"{'PAPER LIVE' if DRY_RUN else 'LIVE'}\n"
           f"STATUS: OPEN\n"
           f"{direction_str}: {entry_price:,.2f}\n"
           f"TP/SL: {tp_price:,.2f} - {sl_price:,.2f}\n"
           f"ASSET: MNQ\n"
           f"SIZE: {NC} Contracts\n"
           f"ATR: {atr:.2f}\n"
           f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    send(msg)

    # ── 4. Monitorea la posición ─────────────────────────────────────────────
    result = None
    exit_price = entry_price

    while True:
        now = ct_now()
        t = now.hour * 60 + now.minute

        # Cierre forzado a las 14:30 CT
        if t >= 14*60+30:
            bars = fetch_intraday("MNQ=F")
            exit_price = float(bars.iloc[-1]['close']) if bars is not None and len(bars) > 0 else entry_price
            result = "FLATTEN"
            log.info(f"[{now.strftime('%H:%M')} CT] Cierre forzado @ {exit_price:.2f}")
            break

        bars = fetch_intraday("MNQ=F")
        if bars is None or bars.empty:
            log.info(f"[{now.strftime('%H:%M')} CT] Sin datos, reintentando...")
            time.sleep(POLL_INTERVAL)
            continue

        price = float(bars.iloc[-1]['close'])
        unreal = (price - entry_price) * side * MNQ_POINT * NC

        if side == 1:
            if price <= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price >= tp_price:
                exit_price = tp_price; result = "TP"; break
        else:
            if price >= sl_price:
                exit_price = sl_price; result = "SL"; break
            if price <= tp_price:
                exit_price = tp_price; result = "TP"; break

        log.info(f"[{now.strftime('%H:%M')} CT] {direction_str} @ {price:.2f} | unreal={unreal:+.2f} | TP={tp_price:.2f} SL={sl_price:.2f}")
        time.sleep(POLL_INTERVAL)

    # ── 5. Calcula PnL y notifica ─────────────────────────────────────────────
    pnl = (exit_price - entry_price) * side * MNQ_POINT * NC
    log.info(f"EXIT {result} @ {exit_price:.2f} | PnL={pnl:+.2f}")

    msg = (f"GLITCH CLOSED - COMBO2D\n"
           f"{'PAPER LIVE' if DRY_RUN else 'LIVE'} | {result}\n"
           f"{direction_str}: {entry_price:,.2f} → {exit_price:,.2f}\n"
           f"PnL: ${pnl:+,.2f} USD\n"
           f"ASSET: MNQ\n"
           f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    send(msg)

    paper_log.append({
        "date": today_str, "signal": True, "side": side,
        "direction": direction_str, "entry": entry_price,
        "exit": exit_price, "result": result,
        "pnl": round(pnl, 2), "atr": round(atr, 2),
        "tp_pts": round(tp_pts, 2), "sl_pts": round(sl_pts, 2),
        "nc": NC, "dry_run": DRY_RUN
    })
    save_log(paper_log)

    # Resumen acumulado
    total_pnl = sum(e.get('pnl', 0) for e in paper_log)
    wins  = sum(1 for e in paper_log if e.get('result') == 'TP')
    total = sum(1 for e in paper_log if e.get('result') in ('TP','SL','FLATTEN'))
    wr    = wins/total if total > 0 else 0

    summary = (f"GLITCH - COMBO2D | DAILY SUMMARY\n"
               f"Trades: {total}\n"
               f"Win Rate: {wr:.1%}\n"
               f"PnL Total: ${total_pnl:+,.2f} USD")
    send(summary)
    log.info("Done — saliendo")

if __name__ == "__main__":
    run()
