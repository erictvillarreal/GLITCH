import sys, numpy as np, pandas as pd
sys.path.insert(0, '/workspaces/GLITCH/glitch')
from core.funded_account import XFAAccount, XFA_50K, XFAStatus
from zoneinfo import ZoneInfo

CT = ZoneInfo('America/Chicago')
prices_mes = pd.read_parquet('data_cache/mes_5min_2y.parquet')
prices_mnq = pd.read_parquet('data_cache/mnq_5min_2y.parquet')

def build_daily(prices):
    local = prices.copy()
    local.index = local.index.tz_convert(CT)
    daily = local.resample('1D').agg({'open':'first','close':'last'})
    daily = daily[(daily['open']>0)&(daily['close']>0)]
    daily['ret']      = (daily['close']-daily['open'])/daily['open']
    daily['ret_prev'] = daily['ret'].shift(1)
    daily['ret_2d']   = daily['ret'].shift(2)
    return daily.dropna()

daily_mes = build_daily(prices_mes)
daily_mnq = build_daily(prices_mnq)
common    = daily_mes.index.intersection(daily_mnq.index)
daily_mes = daily_mes.loc[common]
daily_mnq = daily_mnq.loc[common]

local_mes = prices_mes.copy()
local_mes.index = local_mes.index.tz_convert(CT)
local_mes['t']    = local_mes.index.hour*60 + local_mes.index.minute
local_mes['date'] = local_mes.index.date
local_mes['pos']  = np.arange(len(local_mes))
rth = local_mes[local_mes['t']==9*60+30].groupby('date').first()

MES_PT = 5.0
NC     = 10

def gen_sigs(d_mes, d_mnq, rth):
    rows = []
    for d in d_mes.index:
        rm = d_mes.loc[d]
        if d not in d_mnq.index: continue
        rn = d_mnq.loc[d]
        if np.sign(rm.ret_2d)==np.sign(rm.ret_prev): continue
        if np.sign(rn.ret_2d)==np.sign(rn.ret_prev): continue
        ms = 1 if rm.ret_2d>0 else -1
        ns = 1 if rn.ret_2d>0 else -1
        if ms!=ns: continue
        dd = d.date() if hasattr(d,'date') else d
        if dd not in rth.index: continue
        rows.append({'entry_idx':int(rth.loc[dd,'pos']),'side':ms,'date':dd})
    return pd.DataFrame(rows)

def label_fixed(prices, sig, tp_pts, sl_pts, max_bars=66):
    records = []
    close = prices['close'].values
    high  = prices['high'].values
    low   = prices['low'].values
    n     = len(prices)
    for _, row in sig.iterrows():
        idx  = int(row['entry_idx'])
        side = int(row['side'])
        if idx >= n-1: continue
        ep   = close[idx]
        tp_p = ep + side*tp_pts
        sl_p = ep - side*sl_pts
        label = 0; exit_price = ep
        for j in range(idx+1, min(idx+max_bars+1, n)):
            if side==1:
                if low[j]  <= sl_p: label=-1; exit_price=sl_p; break
                if high[j] >= tp_p: label= 1; exit_price=tp_p; break
            else:
                if high[j] >= sl_p: label=-1; exit_price=sl_p; break
                if low[j]  <= tp_p: label= 1; exit_price=tp_p; break
        pnl = (exit_price-ep)*side*MES_PT*NC
        records.append({'date':row['date'],'label':label,'pnl':pnl})
    return pd.DataFrame(records)

def sim_xfa(daily_pnl, n_paths=2000, seed=7):
    np.random.seed(seed)
    total = []
    for _ in range(n_paths):
        acct=XFAAccount(XFA_50K); pusd=0
        for _ in range(500):
            if not acct.is_alive: break
            pnl=float(np.random.choice(daily_pnl))
            acct.start_day(); acct.record_trade_pnl(pnl); acct.end_of_day()
            if not acct.is_alive: break
            if acct.status==XFAStatus.PAYOUT_ELIGIBLE:
                pusd+=acct.request_payout()
        total.append(pusd)
    return np.mean(total), np.mean([u>0 for u in total])

sig_all = gen_sigs(daily_mes, daily_mnq, rth)

print('='*75)
print('CEREBRO 2 — Grid TP/SL fijos en puntos | NC=10 MES')
print('Objetivo: maximizar avg_total_usd extraido del XFA')
print('='*75)
print(f'{"TP":>5} {"SL":>5} {"RR":>5} {"N":>5} {"WR":>7} {"EV/d":>8} {"dias150":>8} {"avg_xfa":>10} {"p1pay":>7}')
print('-'*75)

best = None
results = []
for tp in [2.0, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0]:
    for sl in [1.0, 1.5, 2.0, 3.0, 4.0]:
        if tp <= sl: continue
        labels = label_fixed(prices_mes, sig_all, tp, sl)
        if len(labels) < 20: continue
        wr  = (labels['label']==1).mean()
        daily_pnl = labels.groupby('date')['pnl'].sum().values
        ev  = daily_pnl.mean()
        d150 = (daily_pnl>=150).mean()
        avg_xfa, p1 = sim_xfa(daily_pnl)
        rr = tp/sl
        results.append((tp,sl,rr,len(labels),wr,ev,d150,avg_xfa,p1))
        m = ' <<<' if avg_xfa>5000 else (' <--' if avg_xfa>2000 else '')
        print(f'{tp:>5.1f} {sl:>5.1f} {rr:>5.2f} {len(labels):>5} {wr:>7.1%} {ev:>+8.1f} {d150:>8.1%} {avg_xfa:>10.0f} {p1:>7.1%}{m}')

results.sort(key=lambda x: -x[7])
print()
print('TOP 3 por avg_xfa:')
for r in results[:3]:
    print(f'  TP={r[0]} SL={r[1]} RR={r[2]:.2f} WR={r[4]:.1%} EV={r[5]:+.1f} dias150={r[6]:.1%} avg_xfa=${r[7]:.0f}')
