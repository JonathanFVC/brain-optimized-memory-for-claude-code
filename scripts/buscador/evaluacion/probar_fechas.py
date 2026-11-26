"""Prueba del analizador de fechas en español de buscar_sesiones.py (hoy fijo = 2026-11-25). Uso: python3 -I scripts/buscador/evaluacion/probar_fechas.py
«hoy» no debe tapar otra expresión de fecha."""
import datetime, importlib.util, sys
from pathlib import Path

sp = importlib.util.spec_from_file_location("bs", Path(__file__).resolve().parents[1] / "buscar_sesiones.py"); bs = importlib.util.module_from_spec(sp); sp.loader.exec_module(bs)
hoy = datetime.date(2026, 11, 25); D = datetime.date
CASOS = [
    ("El mes pasado hablamos de X, ¿cómo lo cambiaría hoy?", (D(2026, 10, 1), D(2026, 10, 31))),
    ("la semana pasada, y hoy sigue igual", (D(2026, 11, 16), D(2026, 11, 22))),
    ("en octubre vimos esto, hoy qué hacemos", (D(2026, 10, 1), D(2026, 10, 31))),
    ("qué hicimos hoy", (D(2026, 11, 25), D(2026, 11, 25))),
    ("qué query corrimos ayer", (D(2026, 11, 24), D(2026, 11, 24))),
    ("qué dijimos el 12 de noviembre", (D(2026, 11, 12), D(2026, 11, 12))),
    ("sin ninguna fecha en la pregunta", None),
]
mal = 0
for q, esp in CASOS:
    r = bs.fechas_es(q, hoy); got = (r[0], r[1]) if r else None; ok = got == esp; mal += not ok
    print("OK   " if ok else "FALLA", q[:56], got)
print(f"{len(CASOS) - mal}/{len(CASOS)} OK"); sys.exit(1 if mal else 0)
