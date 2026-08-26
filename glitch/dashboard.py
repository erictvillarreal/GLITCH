"""
Glitch Dashboard v2 — Terminal UI para Raspberry Pi
"""
import sys, os, time, json, math, random
from datetime import datetime
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")

# ── ANSI ──────────────────────────────────────────────
ESC = '\033'
def ansi(*codes): return f"{ESC}[{';'.join(str(c) for c in codes)}m"
def move(r,c):    return f"{ESC}[{r};{c}H"
def clear_screen():  print(f"{ESC}[2J{ESC}[H", end='')
def hide_cursor():   print(f"{ESC}[?25l", end='')
def show_cursor():   print(f"{ESC}[?25h", end='')

# Colors
RESET   = ansi(0)
BOLD    = ansi(1)
DIM     = ansi(2)
BLACK   = ansi(30)
RED     = ansi(91)
GREEN   = ansi(92)
YELLOW  = ansi(93)
BLUE    = ansi(94)
MAGENTA = ansi(95)
CYAN    = ansi(96)
WHITE   = ansi(97)
BG_BLACK= ansi(40)
BG_NAVY = ansi(48,5,17)
BG_DARK = ansi(48,5,232)
BG_GRAY = ansi(48,5,236)

def rgb(r,g,b):    return ansi(38,2,r,g,b)
def bg_rgb(r,g,b): return ansi(48,2,r,g,b)

# Glitch colors
GLITCH_GOLD  = rgb(255,200,0)
GLITCH_BLUE  = rgb(0,180,255)
GLITCH_GREEN = rgb(0,255,140)
GLITCH_RED   = rgb(255,60,60)
GLITCH_DIM   = rgb(80,80,100)
BG_PANEL     = bg_rgb(12,12,20)
BG_HEADER    = bg_rgb(0,20,40)
BG_ACCENT    = bg_rgb(0,40,80)

# ── State ─────────────────────────────────────────────
def load_state(path=".glitch_state.json"):
    try:
        with open(path) as f: return json.load(f)
    except:
        return {"daily_pnls":[], "total_trades":0}

def load_xfa_state(path=".glitch_xfa_state.json"):
    try:
        with open(path) as f: return json.load(f)
    except:
        return {"daily_pnls":[], "winning_days":0,
                "total_payout_amount":0.0}

def load_live(path=".glitch_live.json"):
    try:
        with open(path) as f: return json.load(f)
    except:
        return {"status":"waiting","price":5847.25,
                "position":0,"tp":0,"sl":0,
                "entry":0,"pnl":0,
                "prices":[5820+random.uniform(-5,5)
                          for _ in range(60)]}

# ── Drawing primitives ────────────────────────────────
def box(w, title="", color=GLITCH_BLUE):
    tl,tr,bl,br = '╔','╗','╚','╝'
    h,v = '═','║'
    if title:
        t   = f" {title} "
        pad = w - len(title) - 4
        top = f"{tl}{h*2}{color}{BOLD}{t}{RESET}{color}{h*pad}{tr}"
    else:
        top = f"{tl}{h*(w-2)}{tr}"
    bot = f"{bl}{h*(w-2)}{br}"
    return color+top+RESET, color+bot+RESET, color+v+RESET

def hbar(value, total, width, 
         fill_color=GLITCH_GREEN,
         empty_color=GLITCH_DIM,
         fill_char='█', empty_char='░'):
    if total <= 0: return empty_color + empty_char*width + RESET
    pct  = min(max(value/total, 0), 1.0)
    done = int(pct * width)
    return (fill_color + fill_char*done +
            empty_color + empty_char*(width-done) + RESET)

def sparkline(prices, width=40, height=8,
               entry=0, tp=0, sl=0):
    """ASCII candlestick-style chart."""
    if not prices or len(prices) < 2:
        return [GLITCH_DIM + ' '*width + RESET]*height

    data  = prices[-width:]
    mn    = min(data) - 1
    mx    = max(data) + 1
    rng   = mx - mn
    rows  = []

    for row in range(height):
        frac  = 1.0 - row/(height-1)
        level = mn + frac*rng
        line  = ''

        # Price levels for TP/SL
        is_tp = tp > 0 and abs(level-tp) < rng/(height*1.8)
        is_sl = sl > 0 and abs(level-sl) < rng/(height*1.8)
        is_en = entry > 0 and abs(level-entry) < rng/(height*1.8)

        for i, p in enumerate(data):
            prev  = data[i-1] if i > 0 else p
            is_up = p >= prev

            if abs(p - level) < rng/(height*1.5):
                c = GLITCH_GREEN if is_up else GLITCH_RED
                line += c + ('▲' if is_up else '▼') + RESET
            elif p > level:
                line += GLITCH_BLUE + '│' + RESET
            else:
                line += ' '

        # Add level labels
        if is_tp:
            label = f" {GLITCH_GREEN}{BOLD}◄ TP {tp:.2f}{RESET}"
        elif is_sl:
            label = f" {GLITCH_RED}{BOLD}◄ SL {sl:.2f}{RESET}"
        elif is_en:
            label = f" {YELLOW}{BOLD}◄ IN {entry:.2f}{RESET}"
        else:
            label = ''

        # Pad line
        line += ' '*(width - len(data))
        rows.append(line + label)

    return rows

def pnl_str(pnl):
    if pnl > 0:  return f"{GLITCH_GREEN}{BOLD}+${pnl:.2f}{RESET}"
    if pnl < 0:  return f"{GLITCH_RED}{BOLD}-${abs(pnl):.2f}{RESET}"
    return f"{GLITCH_DIM}$0.00{RESET}"

# ── Main render ───────────────────────────────────────
def render(mode="combine", demo=False):
    hide_cursor()
    clear_screen()

    now    = datetime.now(CT)
    state  = load_state()
    xstate = load_xfa_state()
    live   = load_live()

    # Data
    daily_pnls   = state.get("daily_pnls", [])
    profits      = [p for p in daily_pnls if p > 0]
    total_profit = sum(profits)
    best_day     = max(profits, default=0)
    wins         = len(profits)
    total_t      = len([p for p in daily_pnls if p != 0])
    wr           = wins/total_t if total_t else 0
    days         = len(daily_pnls)
    cons         = best_day/total_profit if total_profit > 0 else 0

    price  = live.get("price", 5847.25)
    status = live.get("status", "waiting")
    pos    = live.get("position", 0)
    tp     = live.get("tp", 0.0)
    sl     = live.get("sl", 0.0)
    entry  = live.get("entry", 0.0)
    pnl    = live.get("pnl", 0.0)
    prices = live.get("prices", [price]*60)

    W = 60  # total width

    # ══ HEADER ═══════════════════════════════════════
    print(BG_HEADER + ' '*W + RESET)
    title_l = f"  {GLITCH_GOLD}{BOLD}⚡ GLITCH{RESET}{BG_HEADER}"
    mode_s  = f"{'COMBINE' if mode=='combine' else 'XFA'}"
    title_r = f"{GLITCH_BLUE}{BOLD}{mode_s}{RESET}{BG_HEADER}  "
    time_s  = f"{WHITE}{now.strftime('%a %d %b  %H:%M:%S CT')}{RESET}{BG_HEADER}"
    print(BG_HEADER + title_l +
          ' '*(W - len(mode_s) - len(now.strftime('%a %d %b  %H:%M:%S CT')) - 14) +
          time_s + '  ' + RESET)
    print(BG_HEADER + ' '*W + RESET)
    print()

    # ══ PRICE + STATUS ════════════════════════════════
    prev  = prices[-2] if len(prices) > 1 else price
    chg   = price - prev
    p_col = GLITCH_GREEN if chg >= 0 else GLITCH_RED
    chg_s = f"{'▲' if chg>=0 else '▼'}{abs(chg):.2f}"

    status_map = {
        "waiting":     f"{YELLOW}⏳ Esperando señal ORB...{RESET}",
        "in_position": f"{GLITCH_GREEN}{BOLD}🟢 EN POSICIÓN{RESET}",
        "no_signal":   f"{GLITCH_DIM}⚪ Sin señal hoy{RESET}",
        "done":        f"{GLITCH_BLUE}✓ Trade completado{RESET}",
        "flat":        f"{GLITCH_DIM}─ Flat{RESET}",
        "auth_failed": f"{GLITCH_RED}✗ Error de conexión{RESET}",
    }
    status_disp = status_map.get(status, f"{WHITE}{status}{RESET}")
    dir_s = ""
    if pos == 1:  dir_s = f"  {GLITCH_GREEN}▲ LONG{RESET}"
    if pos == -1: dir_s = f"  {GLITCH_RED}▼ SHORT{RESET}"

    print(f"  {p_col}{BOLD}MES  {price:>10.2f}{RESET}  "
          f"{p_col}{chg_s}{RESET}"
          f"{'  pts':}{GLITCH_DIM}")
    print(f"  {status_disp}{dir_s}")
    if pos != 0 and entry > 0:
        print(f"  {GLITCH_DIM}Entry: {entry:.2f}  "
              f"PnL: {pnl_str(pnl)}  "
              f"Contracts: {abs(pos)*3 if mode=='combine' else abs(pos)*5} MES{RESET}")
    print()

    # ══ CHART ════════════════════════════════════════
    print(f"  {GLITCH_DIM}{'─'*52}{RESET}")
    chart = sparkline(prices, width=48, height=7,
                       entry=entry if pos!=0 else 0,
                       tp=tp if pos!=0 else 0,
                       sl=sl if pos!=0 else 0)
    for row in chart:
        print(f"  {row}")

    # Price scale
    mn = min(prices[-48:]) if prices else price-10
    mx = max(prices[-48:]) if prices else price+10
    print(f"  {GLITCH_DIM}└{'─'*47}┘{RESET}")
    print(f"  {GLITCH_DIM}{mn:.1f}"
          f"{' '*(44-len(f'{mn:.1f}'))}{mx:.1f}{RESET}")
    print()

    # ══ COMBINE / XFA PROGRESS ════════════════════════
    print(f"  {GLITCH_DIM}{'─'*52}{RESET}")

    if mode == "combine":
        print(f"  {GLITCH_GOLD}{BOLD}▸ TRADING COMBINE{RESET}")
        print()

        # Profit target
        bar_p = hbar(total_profit, 3000, 36,
                      GLITCH_GREEN if total_profit < 2400 else GLITCH_GOLD)
        pct_p = min(total_profit/3000*100,100) if total_profit else 0
        print(f"  {WHITE}Profit Target{RESET}  "
              f"${total_profit:>6,.0f} / $3,000")
        print(f"  {bar_p}  {GLITCH_GREEN}{pct_p:.0f}%{RESET}")
        print()

        # MLL buffer
        buffer = 2000.0  # simplified
        bar_m  = hbar(buffer, 2000, 36,
                       GLITCH_GREEN if buffer > 800 else GLITCH_RED)
        print(f"  {WHITE}MLL Buffer{RESET}     "
              f"${buffer:>6,.0f} / $2,000")
        print(f"  {bar_m}  "
              f"{'🟢' if buffer > 800 else '🔴'}")
        print()

        # Consistency
        cons_color = GLITCH_RED if cons > 0.45 else \
                     YELLOW if cons > 0.35 else GLITCH_GREEN
        bar_c = hbar(cons, 0.50, 36,
                      cons_color, GLITCH_DIM)
        print(f"  {WHITE}Consistency{RESET}    "
              f"{cons:.1%} / 50%  "
              f"{'⚠ CUIDADO' if cons > 0.40 else 'OK'}")
        print(f"  {bar_c}")

    else:  # XFA
        wd    = xstate.get("winning_days", 0)
        tp_t  = xstate.get("total_payout_amount", 0)
        print(f"  {GLITCH_GOLD}{BOLD}▸ EXPRESS FUNDED ACCOUNT{RESET}")
        print()

        # Winning days
        bar_w = hbar(wd, 5, 36, GLITCH_GOLD)
        print(f"  {WHITE}Winning Days{RESET}   {wd} / 5")
        print(f"  {bar_w}  "
              f"{'🎯 ELIGIBLE PAYOUT!' if wd >= 5 else f'{5-wd} días más'}")
        print()

        # Balance toward $55k
        bal = live.get("balance", 50000)
        bar_b = hbar(bal-50000, 5000, 36, GLITCH_BLUE)
        print(f"  {WHITE}Balance{RESET}        "
              f"${bal:>8,.0f} / $55,000")
        print(f"  {bar_b}")
        print()

        # Total payouts
        print(f"  {WHITE}Realizados{RESET}     "
              f"{GLITCH_GREEN}{BOLD}${tp_t:>,.0f}{RESET} total")

    print()
    print(f"  {GLITCH_DIM}{'─'*52}{RESET}")

    # ══ STATS ROW ════════════════════════════════════
    wr_col = GLITCH_GREEN if wr >= 0.40 else YELLOW
    print(f"  {GLITCH_DIM}Día {days:>3}{RESET}  "
          f"{WHITE}WR{RESET} {wr_col}{wr:.1%}{RESET}  "
          f"{WHITE}Trades{RESET} {total_t}  "
          f"{WHITE}Best{RESET} ${best_day:.0f}  "
          f"{WHITE}EV/día{RESET} "
          f"{pnl_str(sum(daily_pnls)/days if days else 0)}")

    # ══ FOOTER ════════════════════════════════════════
    print()
    print(f"  {GLITCH_DIM}Actualiza cada 10s  ·  "
          f"{'demo mode' if demo else 'LIVE'}  ·  "
          f"Ctrl+C para salir{RESET}")
    print()

    sys.stdout.flush()

# ── Demo mode: genera precios simulados ───────────────
_demo_prices = [5820 + i*0.3 + random.uniform(-3,3)
                for i in range(60)]
_demo_state  = {"daily_pnls": [90,-45,90,90,-45,90,
                                -45,90,90,0,90,-45,
                                90,90,0,-45,90,90],
                "total_trades": 18}
_demo_live   = {"status":"in_position","price":5847.25,
                "position":1,"tp":5853.25,"sl":5844.25,
                "entry":5847.25,"pnl":37.50,
                "prices":_demo_prices}

def save_demo_files():
    with open(".glitch_state.json","w") as f:
        json.dump(_demo_state, f)
    with open(".glitch_live.json","w") as f:
        json.dump(_demo_live, f)

# ── Main ──────────────────────────────────────────────
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode",     default="combine",
                   choices=["combine","xfa"])
    p.add_argument("--demo",     action="store_true")
    p.add_argument("--interval", type=int, default=10)
    args = p.parse_args()

    if args.demo:
        save_demo_files()

    try:
        while True:
            if args.demo:
                # Simulate price movement
                last = _demo_live["prices"][-1]
                new  = last + random.uniform(-2, 2.5)
                _demo_live["prices"].append(new)
                _demo_live["price"] = new
                _demo_live["pnl"]   = (new - _demo_live["entry"]) * 3 * 5
                save_demo_files()
            render(mode=args.mode, demo=args.demo)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        show_cursor()
        clear_screen()
        print("Glitch dashboard stopped.")

if __name__ == "__main__":
    main()
