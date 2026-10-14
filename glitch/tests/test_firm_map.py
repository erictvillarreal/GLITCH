"""Esquema del mapa de firmas: toda fila declara de donde sale el dato y ninguna cifra 'no leida' se presenta como verificada."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.firm_map import FIRMAS, CAMPOS

def test_schema_and_levels():
    names = [r["firma"] for r in FIRMAS]
    assert len(names) == len(set(names)) >= 30
    for r in FIRMAS:
        assert r["fuente"] in ("directa", "oficial_resumen", "terceros", "nada")
        assert r["automatizacion"] in ("PERMITIDA_COND", "MANUAL_SEMI", "PROHIBIDA", "CONTRADICTORIA", "DESCONOCIDA")
        assert all(k in r for k in ("firma", "fuente", "automatizacion", "automatizacion_nota"))

def test_only_directly_read_firms_are_marked_directa_and_are_the_known_three():
    assert sorted(r["firma"] for r in FIRMAS if r["fuente"] == "directa") == ["Apex Trader Funding", "Bulenox", "Topstep"]

def test_nothing_found_means_no_permission_claim():
    for r in FIRMAS:
        if r["fuente"] == "nada":
            assert r["automatizacion"] == "DESCONOCIDA"

def test_third_party_only_firms_are_never_permitted_without_a_caveat():
    for r in FIRMAS:
        if r["fuente"] == "terceros" and r["automatizacion"] == "PERMITIDA_COND":
            assert "NO leid" in r["automatizacion_nota"] or "terceros" in r["automatizacion_nota"] or "resumen" in r["automatizacion_nota"]
