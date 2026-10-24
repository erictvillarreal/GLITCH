"""BarDays con ancho y contratos por dia (Parte G/H): la politica solo decide si opera (nc > 0); el ancho W_t (SL = TP) y los contratos nc_t salen de arreglos por dia."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from daydata import sim_day
from xfa_engine import BarDays


class ScaledDays(BarDays):
    def __init__(self, *a, Wd, ncd, **kw):
        super().__init__(*a, **kw); self.Wd, self.ncd, self._sc = np.asarray(Wd), np.asarray(ncd), {}

    def tab(self, side, ncv, w):
        key = (side, ncv, w)
        if key not in self._sc:
            K = np.empty((self.nb, self.dd.D), np.int8); Pn = np.empty((self.nb, self.dd.D))
            for b in range(self.nb):
                kk, pp = sim_day(self.dd, side, ncv, max(b * self.step, 1e-9), slip=self.slips[0], exit_slip=self.exit_slip, sl=w, tp=w, order=self.order, fee=self.fee, tick_usd=self.tick_usd, drift=self.drift, stop_frac=self.stop_frac)
                K[b], Pn[b] = kk, pp
            self._sc[key] = (K, Pn)
        return self._sc[key]

    def resolve(self, idx, si, side, nc, cush, sl):
        n = len(idx); kind = np.full(n, 3, np.int8); pnl = np.zeros(n)
        bins = np.clip(np.floor(cush / self.step + 1e-9).astype(int), 0, self.nb - 1)
        w_i, n_i = self.Wd[idx], self.ncd[idx]
        for w in np.unique(w_i):
            for ncv in np.unique(n_i[w_i == w]):
                for sd in (1, -1):
                    m = (nc > 0) & (w_i == w) & (n_i == ncv) & (side == sd)
                    if not m.any(): continue
                    K, Pn = self.tab(sd, int(ncv), int(w)); kind[m] = K[bins[m], idx[m]]; pnl[m] = Pn[bins[m], idx[m]]
        return kind, pnl
