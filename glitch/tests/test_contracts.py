"""
Tests para execution/contracts.py::check_expiry_alerts() -- checkpoints
de vencimiento (09-sep-2026), ver GLITCH_RESEARCH_LOG.md.

Cubre: dispara exactamente en los checkpoints (10,5,2,1), no dispara en
dias intermedios, y -- el caso critico -- NO pierde un checkpoint
cuando un feriado hace que el conteo salte 2 dias habiles en vez de 1
entre dos corridas reales.
"""
import datetime as real_dt
import os

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")

import execution.contracts as contracts


class _FakeDate(real_dt.date):
    """Subclase de date con .today() fijo -- para controlar 'hoy' en los
    tests sin mockear todo el modulo datetime."""
    _today = real_dt.date(2026, 1, 1)

    @classmethod
    def today(cls):
        return cls._today


def _set_today(monkeypatch, d: real_dt.date):
    _FakeDate._today = d
    monkeypatch.setattr(contracts.dt, "date", _FakeDate)


def _cache_for(ltd: real_dt.date) -> dict:
    return {"MES": ("MESU6", ltd.isoformat())}


class TestPreviousTradingDay:
    def test_skips_weekend(self):
        # Lunes 2026-09-14 -> viernes anterior 2026-09-11
        assert contracts._previous_trading_day(real_dt.date(2026, 9, 14)) == real_dt.date(2026, 9, 11)

    def test_skips_holiday(self):
        # Martes 2026-09-08 -> feriado lunes 2026-09-07 -> viernes 2026-09-04
        assert contracts._previous_trading_day(real_dt.date(2026, 9, 8)) == real_dt.date(2026, 9, 4)

    def test_plain_weekday(self):
        assert contracts._previous_trading_day(real_dt.date(2026, 9, 9)) == real_dt.date(2026, 9, 8)


class TestCheckExpiryAlertsCheckpoints:
    def test_fires_exactly_at_checkpoint_10(self, monkeypatch):
        # dia habil anterior (miercoles 2026-09-09) -> days_left=11
        # hoy (jueves 2026-09-10) -> days_left=10
        ltd = real_dt.date(2026, 9, 24)
        _set_today(monkeypatch, real_dt.date(2026, 9, 10))
        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - COMBINE - MES")
        assert len(sent) == 1
        assert "checkpoint 10" in sent[0]
        assert "S10GLITCH - COMBINE - MES" in sent[0]
        assert "STATUS: CONTRATO PROXIMO A VENCER" in sent[0]

    def test_does_not_fire_between_checkpoints(self, monkeypatch):
        # days_left=8 hoy, 9 ayer -- ningun checkpoint en (8,9)
        ltd = real_dt.date(2026, 9, 22)
        _set_today(monkeypatch, real_dt.date(2026, 9, 10))
        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - COMBINE - MES")
        assert sent == []

    def test_does_not_refire_day_after_checkpoint(self, monkeypatch):
        # dia siguiente a un checkpoint ya disparado -- no debe volver a disparar
        ltd = real_dt.date(2026, 9, 23)  # days_left=9 hoy, 10 ayer -> checkpoint 10 YA se disparo ayer
        _set_today(monkeypatch, real_dt.date(2026, 9, 10))
        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - COMBINE - MES")
        assert sent == []

    def test_holiday_gap_does_not_lose_checkpoint(self, monkeypatch):
        """
        CASO CRITICO: el feriado del 07-sep-2026 (lunes) hace que el
        scheduler no corra ese dia. La ultima corrida real fue el
        viernes 04-sep (days_left=11 para un LTD que cae 15 dias
        habiles despues); la siguiente corrida real es el martes 08-sep
        (days_left=9, saltandose el 10 exacto). El checkpoint 10 NO debe
        perderse -- debe disparar en la corrida del martes.
        """
        # Buscar un LTD tal que: dia habil anterior real (04-sep, viernes)
        # tenga days_left=11, y hoy (08-sep, martes) tenga days_left=9.
        # np.busday_count(04-sep, LTD) = 11 y np.busday_count(08-sep, LTD) = 9
        # (viernes->martes son 2 dias habiles de por medio: lunes+martes,
        # pero busday_count no conoce el feriado del lunes, cuenta 2 igual
        # solo si avanza el conteo -- aqui alcanza con elegir LTD fijo y
        # verificar los valores resultantes directamente.)
        ltd = real_dt.date(2026, 9, 19)
        _set_today(monkeypatch, real_dt.date(2026, 9, 8))  # martes, primer dia habil tras el feriado

        # Confirmar la premisa del escenario antes de confiar en el resultado
        assert contracts._previous_trading_day(real_dt.date(2026, 9, 8)) == real_dt.date(2026, 9, 4)
        days_left_today = int(__import__("numpy").busday_count(real_dt.date(2026, 9, 8), ltd))
        days_left_prev = int(__import__("numpy").busday_count(real_dt.date(2026, 9, 4), ltd))
        assert days_left_prev == 11 and days_left_today == 9, (
            f"Premisa del escenario no se cumple (prev={days_left_prev}, today={days_left_today}) "
            f"-- ajustar el LTD del test."
        )

        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - COMBINE - MES")
        assert len(sent) == 1, "El checkpoint 10 se perdio en el salto por feriado"
        assert "checkpoint 10" in sent[0]

    def test_no_alert_when_far_from_any_checkpoint(self, monkeypatch):
        ltd = real_dt.date(2026, 12, 18)
        _set_today(monkeypatch, real_dt.date(2026, 9, 10))
        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - COMBINE - MES")
        assert sent == []

    def test_uses_caller_prefix_verbatim_no_hardcoding(self, monkeypatch):
        ltd = real_dt.date(2026, 9, 24)
        _set_today(monkeypatch, real_dt.date(2026, 9, 10))
        sent = []
        contracts.check_expiry_alerts(_cache_for(ltd), sent.append, "S10GLITCH - XFA - MGC")
        assert sent[0].startswith("S10GLITCH - XFA - MGC\n")
        assert "GEOMETRY" not in sent[0]
