"""
Glitch — Logging con timestamp SIEMPRE en America/Chicago (07-sep-2026)
==========================================================================
UNICA fuente de verdad del setup de logging para CUALQUIER scheduler
(geometry, combo2d, geometry_mgc, futuros) -- reemplaza el patron
duplicado `logging.basicConfig(format="%(asctime)s CT ...")` que existia
identico en 4 archivos.

POR QUE: ese patron dependia SILENCIOSAMENTE de que el TZ del contenedor
ya fuera America/Chicago -- `%(asctime)s` usa `time.localtime()` por
default, y el "CT" en el format string era un literal, no algo derivado
del valor real. Funcionaba en Railway SOLO porque la variable de entorno
TZ=America/Chicago esta seteada ahi -- si esa variable alguna vez
faltara o cambiara (default tipico de un contenedor Docker: UTC), los
logs mostrarian hora UTC etiquetada incorrectamente como "CT", sin
ningun error visible. Encontrado el 07-sep-2026 mientras se documentaba
el historial del proyecto para el reporte de GitHub Pages -- nunca
habia sido un bug "ya arreglado" de la busqueda de edge original, pese
a haberse mencionado como tal -- ver GLITCH_RESEARCH_LOG.md.

Verificado con prueba manual antes de aplicar este fix (ver
tests/test_ct_logging.py para la version permanente):
    TZ=America/Chicago -> log correcto (coincide con CT real)
    TZ=UTC             -> log ANTES mostraba hora UTC etiquetada "CT"
                          (bug); AHORA (con este modulo) sigue mostrando
                          CT real sin importar el TZ del proceso.
"""
from __future__ import annotations
import logging
import sys
import datetime as dt
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")


class CTFormatter(logging.Formatter):
    """Formatter cuyo timestamp SIEMPRE refleja America/Chicago,
    independientemente de time.localtime()/el TZ del proceso."""

    def converter(self, timestamp):
        return dt.datetime.fromtimestamp(timestamp, tz=CT).timetuple()


def setup_ct_logging(logger_name: str) -> logging.Logger:
    """
    Configura logging.root con un handler a stdout y CTFormatter --
    reemplaza logging.basicConfig(format="%(asctime)s CT ...") en
    cualquier scheduler. Llamar UNA vez al inicio del modulo, igual que
    se llamaba basicConfig antes.
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(CTFormatter(fmt="%(asctime)s CT [%(levelname)s] %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    return logging.getLogger(logger_name)
