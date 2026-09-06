"""
Glitch — Tests de execution/ct_logging.py (07-sep-2026)
==========================================================
Regresion directa del bug encontrado el 07-sep-2026: el patron anterior
(logging.basicConfig con format="%(asctime)s CT") dependia
SILENCIOSAMENTE de que el TZ del proceso/contenedor ya fuera
America/Chicago -- funcionaba en Railway solo porque TZ=America/Chicago
esta seteado ahi. Si esa variable faltara (default tipico de Docker:
UTC), los logs mostrarian hora UTC etiquetada incorrectamente como "CT".

Este test simula exactamente ese escenario: fuerza el TZ del PROCESO a
UTC (el caso que rompia el patron viejo) y confirma que el timestamp
logueado sigue reflejando la hora real de Chicago, no UTC.
"""
import os
import sys
import time
import logging
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.ct_logging import CTFormatter, CT


class TestCTFormatter:

    def test_converter_ignores_process_tz(self, monkeypatch):
        """El caso que rompia el patron viejo: TZ del proceso = UTC."""
        monkeypatch.setenv("TZ", "UTC")
        if hasattr(time, "tzset"):
            time.tzset()
        try:
            # Timestamp fijo y conocido: 2026-01-15 18:00:00 UTC
            fixed_utc = dt.datetime(2026, 1, 15, 18, 0, 0, tzinfo=dt.timezone.utc)
            timestamp = fixed_utc.timestamp()

            formatter = CTFormatter(fmt="%(asctime)s CT [%(levelname)s] %(message)s",
                                     datefmt="%Y-%m-%d %H:%M:%S")
            record = logging.LogRecord("test", logging.INFO, __file__, 1, "msg", None, None)
            record.created = timestamp
            formatted_time = formatter.formatTime(record, formatter.datefmt)

            # 18:00 UTC en enero (CST, UTC-6) = 12:00 CT -- NO 18:00
            # (que es lo que el patron viejo hubiera mostrado con TZ=UTC).
            expected_ct = fixed_utc.astimezone(CT).strftime("%Y-%m-%d %H:%M:%S")
            assert formatted_time == expected_ct
            assert formatted_time == "2026-01-15 12:00:00"
            assert formatted_time != fixed_utc.strftime("%Y-%m-%d %H:%M:%S")
        finally:
            if hasattr(time, "tzset"):
                time.tzset()

    def test_converter_correct_in_summer_dst(self, monkeypatch):
        """CDT (UTC-5) en verano -- confirma que respeta DST correctamente, no un offset fijo."""
        monkeypatch.setenv("TZ", "UTC")
        if hasattr(time, "tzset"):
            time.tzset()
        try:
            fixed_utc = dt.datetime(2026, 7, 15, 18, 0, 0, tzinfo=dt.timezone.utc)
            formatter = CTFormatter(fmt="%(asctime)s CT", datefmt="%Y-%m-%d %H:%M:%S")
            record = logging.LogRecord("test", logging.INFO, __file__, 1, "msg", None, None)
            record.created = fixed_utc.timestamp()
            formatted_time = formatter.formatTime(record, formatter.datefmt)

            # 18:00 UTC en julio (CDT, UTC-5) = 13:00 CT
            assert formatted_time == "2026-07-15 13:00:00"
        finally:
            if hasattr(time, "tzset"):
                time.tzset()
