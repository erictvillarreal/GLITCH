"""
Glitch — Paper Trading Store (SQLite)
=======================================
Persistencia local de señales/paper-trades para poder:
  1. Calcular WR / avg_win / avg_loss empiricos en vivo
  2. Saber cuando la muestra ya es estadisticamente significativa
     (usa simulation.grid_search.minimum_sample_size)
  3. Alimentar DailyReturnDist.from_trade_log() con datos REALES
     una vez juntada la muestra -> Monte Carlo con edge validado

No depende de ningun broker: solo guarda filas. El bot de Telegram
y el runner de la estrategia son los que deciden CUANDO llamar a esto.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import pandas as pd

DB_PATH = Path(__file__).parent / "glitch_paper.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    strategy      TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    side          INTEGER NOT NULL,     -- +1 long, -1 short
    entry_price   REAL NOT NULL,
    stop_price    REAL NOT NULL,
    target_price  REAL NOT NULL,
    contracts     INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open',   -- open | win | loss | timeout
    exit_price    REAL,
    exit_at       TEXT,
    pnl_usd       REAL,
    session_date  TEXT NOT NULL,
    telegram_msg_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_session_date ON signals(session_date);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(SCHEMA)
    return conn


@dataclass
class Signal:
    strategy: str
    symbol: str
    side: int
    entry_price: float
    stop_price: float
    target_price: float
    contracts: int
    session_date: str


def log_signal(sig: Signal) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO signals
           (created_at, strategy, symbol, side, entry_price, stop_price,
            target_price, contracts, session_date)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (datetime.now(timezone.utc).isoformat(), sig.strategy, sig.symbol, sig.side,
         sig.entry_price, sig.stop_price, sig.target_price, sig.contracts, sig.session_date),
    )
    conn.commit()
    sig_id = cur.lastrowid
    conn.close()
    return sig_id


def set_telegram_msg_id(sig_id: int, msg_id: int):
    conn = get_conn()
    conn.execute("UPDATE signals SET telegram_msg_id=? WHERE id=?", (msg_id, sig_id))
    conn.commit()
    conn.close()


def close_signal(sig_id: int, status: str, exit_price: float, point_value_usd: float):
    """status: 'win' | 'loss' | 'timeout'"""
    conn = get_conn()
    row = conn.execute("SELECT side, entry_price, contracts FROM signals WHERE id=?", (sig_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"signal {sig_id} not found")
    side, entry_price, contracts = row
    pnl_usd = side * (exit_price - entry_price) * point_value_usd * contracts
    conn.execute(
        "UPDATE signals SET status=?, exit_price=?, exit_at=?, pnl_usd=? WHERE id=?",
        (status, exit_price, datetime.now(timezone.utc).isoformat(), pnl_usd, sig_id),
    )
    conn.commit()
    conn.close()
    return pnl_usd


def open_signals() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM signals WHERE status='open'", conn)
    conn.close()
    return df


def closed_signals(strategy: Optional[str] = None) -> pd.DataFrame:
    conn = get_conn()
    q = "SELECT * FROM signals WHERE status IN ('win','loss','timeout')"
    params = ()
    if strategy:
        q += " AND strategy=?"
        params = (strategy,)
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    return df


def daily_pnl_series(strategy: Optional[str] = None) -> pd.Series:
    df = closed_signals(strategy)
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("session_date")["pnl_usd"].sum()


def running_stats(strategy: Optional[str] = None) -> dict:
    """Estadisticas en vivo de la muestra de paper trading."""
    df = closed_signals(strategy)
    if df.empty:
        return {"n_trades": 0, "n_days": 0, "win_rate": None, "avg_win": None,
                "avg_loss": None, "ev_per_trade": None}
    wins = df.loc[df.status == "win", "pnl_usd"]
    losses = df.loc[df.status == "loss", "pnl_usd"].abs()
    n = len(df)
    return {
        "n_trades": n,
        "n_days": df["session_date"].nunique(),
        "win_rate": round((df.status == "win").mean(), 4),
        "avg_win": round(wins.mean(), 2) if len(wins) else 0.0,
        "avg_loss": round(losses.mean(), 2) if len(losses) else 0.0,
        "ev_per_trade": round(df["pnl_usd"].mean(), 2),
    }
