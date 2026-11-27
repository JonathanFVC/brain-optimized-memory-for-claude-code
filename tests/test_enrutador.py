"""Prueba del enrutador de búsqueda (enrutar_busqueda.py) con mensajes ficticios; sin modelos, sin red, sin tocar tu índice.
Uso: python3 -I tests/test_enrutador.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/buscador"))
import enrutar_busqueda as E

CASOS = [  # (mensaje, buscar, fuente, k, urgente)
    ("Gracias, listo", False, None, 0, False),
    ("súbelo", False, None, 0, False),
    ("explica cómo funciona un hash SHA-256", False, None, 0, False),
    ("¿Qué decidimos ayer sobre el formato del reporte?", True, "conversaciones", 3, False),
    ("¿En qué archivo está la función que exporta el reporte?", True, "carpeta", 5, False),
    ("ABC-123", True, "ambas", 2, False),
    ("revisa el ticket ABC-123 del tracker y dime qué falta", True, "ambas", 2, False),
    ("ABC-123 Exportar reporte\nDescripción: es urgente. Ayer hablamos con el cliente y quedamos en entregarlo hoy.\nCriterios: formato CSV.", True, "ambas", 2, False),
    ("ABC-123 Exportar reporte\nDescripción: pedido del cliente.\nCriterios: formato CSV.\nhazlo YA", True, "ambas", 2, True),
    ("apúrate, ¿qué dijimos del formato del reporte?", True, "conversaciones", 3, True),
    ("vamos a rehacer el modulo de exportación", True, "ambas", 3, False),
]
fallas = 0
for msg, buscar, fuente, k, urgente in CASOS:
    d = E.decidir(msg); ok = (d["buscar"], d["fuente"], d["k"], d["urgente"]) == (buscar, fuente, k, urgente)
    fallas += not ok; print("OK   " if ok else "FALLA", repr(msg[:60]), "→", (d["fuente"] or "no busca"), d["k"], "urgente" if d["urgente"] else "", "" if ok else f"(se esperaba {fuente} {k} {'urgente' if urgente else ''})")
d = E.decidir(CASOS[7][0]); ok = d.get("consulta", "").startswith("ABC-123") and "hablamos" not in d.get("consulta", "")
fallas += not ok; print("OK   " if ok else "FALLA", "ticket pegado: la consulta es el ID y el título, no todo el texto", repr(d.get("consulta")))
print("\n" + ("TODO OK" if not fallas else f"{fallas} FALLAS")); sys.exit(1 if fallas else 0)
