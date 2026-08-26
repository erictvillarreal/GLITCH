import sys, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
sys.path.insert(0, '/workspaces/GLITCH/glitch')
from core.funded_account import XFAAccount, XFA_50K, XFAStatus
from scipy import stats as scipy_stats
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
TP_PTS = 7.5
SL_PTS = 3.0

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

def label_fixed_pts(prices, sig, tp_pts, sl_pts, max_bars=66):
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
        pnl_usd = (exit_price-ep)*side*MES_PT*NC
        records.append({'entry_idx':idx,'side':side,'date':row['date'],
                        'label':label,'pnl_usd':pnl_usd})
    return pd.DataFrame(records)

sig_all = gen_sigs(daily_mes, daily_mnq, rth)
labels  = label_fixed_pts(prices_mes, sig_all, TP_PTS, SL_PTS)

wr  = (labels['label']==1).mean()
ev  = labels['pnl_usd'].mean()
wins = labels[labels['label']==1]['pnl_usd']
loss = labels[labels['label']==-1]['pnl_usd']

print('='*60)
print(f'Cerebro2 — TP={TP_PTS}pts (${TP_PTS*MES_PT*NC:.0f}) SL={SL_PTS}pts (${SL_PTS*MES_PT*NC:.0f})')
print('='*60)
print(f'Trades:    {len(labels)}')
print(f'WR:        {wr:.1%}')
print(f'Avg win:   ${wins.mean():+.1f}' if len(wins) else 'Sin wins')
print(f'Avg loss:  ${loss.mean():+.1f}' if len(loss) else 'Sin losses')
print(f'EV/trade:  ${ev:+.1f}')

daily_pnl = labels.groupby('date')['pnl_usd'].sum().values
print(f'EV/dia:    ${daily_pnl.mean():+.1f}')
print(f'Dias +150: {(daily_pnl>=150).mean():.1%}')

pnl_arr = labels['pnl_usd'].values.copy()
real_ev  = pnl_arr.mean()
sh_evs   = [np.random.shuffle(a := pnl_arr.copy()) or a.mean() for _ in range(1000)]
pct      = np.mean(np.array(sh_evs) < real_ev)
print(f'Reshuffle: {pct:.1%} -> {"EDGE" if pct>0.90 else "RUIDO" if pct<0.75 else "BORDERLINE"}')

n = len(prices_mes)
train_bars, test_bars = 5000, 1000
folds_ev = []; folds_wr = []
i = train_bars
while i + test_bars <= n:
    tp_s = prices_mes.iloc[i:i+test_bars]
    ts, te = tp_s.index[0], tp_s.index[-1]
    dm = daily_mes[(daily_mes.index.date>=ts.date())&(daily_mes.index.date<=te.date())].copy()
    dn = daily_mnq[(daily_mnq.index.date>=ts.date())&(daily_mnq.index.date<=te.date())].copy()
    dm['ret_prev'] = daily_mes['ret'].reindex(dm.index).shift(1)
    dm['ret_2d']   = daily_mes['ret'].reindex(dm.index).shift(2)
    dn['ret_prev'] = daily_mnq['ret'].reindex(dn.index).shift(1)
    dn['ret_2d']   = daily_mnq['ret'].reindex(dn.index).shift(2)
    fs = gen_sigs(dm.dropna(), dn.dropna(), rth)
    if len(fs)<5: i+=test_bars; continue
    fl = label_fixed_pts(prices_mes, fs, TP_PTS, SL_PTS)
    if len(fl)<5: i+=test_bars; continue
    folds_ev.append(fl['pnl_usd'].mean())
    folds_wr.append((fl['label']==1).mean())
    i += test_bars

evs = np.array(folds_ev)
t2, p22 = scipy_stats.ttest_1samp(evs, 0)
p1 = p22/2 if t2>0 else 1.0
print(f'WF:        n={len(evs)} mean_WR={np.mean(folds_wr):.1%} t={t2:.3f} p={p1:.4f} sig5={p1<0.05}')

np.random.seed(7)
total_usd = []
for _ in range(3000):
    acct=XFAAccount(XFA_50K); pusd=0
    for _ in range(500):
        if not acct.is_alive: break
        pnl=float(np.random.choice(daily_pnl))
        acct.start_day(); acct.record_trade_pnl(pnl); acct.end_of_day()
        if not acct.is_alive: break
        if acct.status==XFAStatus.PAYOUT_ELIGIBLE:
            pusd+=acct.request_payout()
    total_usd.append(pusd)
print(f'XFA:       avg=${np.mean(total_usd):.0f} prob_1payout={np.mean([u>0 for u in total_usd]):.1%} median=${np.median(total_usd):.0f}')
