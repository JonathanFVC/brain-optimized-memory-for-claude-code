"""Pruebas del calibrador del enrutador (calibrar_enrutador.py) con datos ficticios; sin modelos, sin red, sin tocar tu registro.
Uso: python3 -I tests/test_calibrador.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/buscador")); import calibrar_enrutador as C
F = 0
def ok(c, t):
    global F; F += not c; print("OK   " if c else "FALLA", t)
def filas(rid, marcas, accion="ambas"):
    fs = [{"id": f"{rid}-{i}", "regla": rid, "accion": accion, "buscar": True, "fuente": "ambas", "motivo": rid} for i in range(len(marcas))]; return fs, [{"id": f["id"], "marca": m} for f, m in zip(fs, marcas)]
R = "pregunta por lo hablado"; d = {"buscar": True, "fuente": "conversaciones", "k": 3, "rutas": False, "tokens_aprox": 580, "motivo": R}
f, m = filas(R, ["v2"] * 24); a, _ = C.accion_vigente(R, C.evidencia(f, m)[R], "v2"); ok(a == "ambas", "24 marcas perfectas aún no desbloquean (arranque: las dos)")
f, m = filas(R, ["v2"] * 26); a, _ = C.accion_vigente(R, C.evidencia(f, m)[R], "v2"); ok(a == "v2", "26 marcas de v2 desbloquean «solo conversaciones»")
f, m = filas(R, ["v2"] * 26 + ["ambas"]); a, _ = C.accion_vigente(R, C.evidencia(f, m)[R], "v2"); ok(a in ("v2", "ambas"), "una marca «ambas» entre 27 no rompe el cálculo")
f, m = filas(R, ["v2"] * 20 + ["ambas"] * 10); a, _ = C.accion_vigente(R, C.evidencia(f, m)[R], "v2"); ok(a == "ambas", "30 % de «ambas» obliga a seguir en las dos")
f, m = filas("comando pegado", ["ninguna"] * 30); a, _ = C.accion_vigente("comando pegado", C.evidencia(f, m)["comando pegado"], "ninguna"); ok(a == "ninguna", "30 marcas «ninguna» desbloquean «en vivo»")
f, m = filas("saludo o respuesta corta", ["v1"] * 40); a, nota = C.accion_vigente("saludo o respuesta corta", C.evidencia(f, m)["saludo o respuesta corta"], "ninguna"); ok(a == "ninguna" and "fija" in nota, "las reglas fijas no se calibran")
f, m = filas("comando pegado", ["v1"] * 12); a, _ = C.accion_vigente("comando pegado", C.evidencia(f, m)["comando pegado"], "ninguna", prior="reglas"); ok(a == "ambas", "prior «reglas»: si la decisión original falla, se amplía")
f, m = filas("comando pegado", [], "ninguna"); a, _ = C.accion_vigente("comando pegado", [], "ninguna", prior="reglas"); ok(a == "ninguna", "prior «reglas» sin datos: decisión original")
# sesgo: una búsqueda estrecha solo aporta marcas que muestran falla
fs = [{"id": "a", "regla": R, "accion": "v2"}, {"id": "b", "regla": R, "accion": "v2"}, {"id": "c", "regla": R, "accion": "ambas"}]; ev = C.evidencia(fs, [{"id": "a", "marca": "v2"}, {"id": "b", "marca": "ambas"}, {"id": "c", "marca": "v2"}])[R]
ok(sorted(ev) == ["ambas", "v2"], "marca de una búsqueda estrecha: cuenta solo si revela falla (b), no si coincide (a)")
ok(C.regla_id("tema propio «deploy» → ambas (enrutador-temas.tsv) · calibrado: v2") == "tema propio «» → ambas (enrutador-temas.tsv)", "regla_id quita lo variable y la nota de calibrado")
r = C.aplicar(d, [], [], prior="ambas"); ok(r["fuente"] == "ambas" and r["tokens_aprox"] == 1040 and "calibrado" in r["motivo"], "arranque: aplicar amplía a las dos")
r = C.aplicar(d, [], [], prior="reglas"); ok(r["fuente"] == "conversaciones", "prior «reglas»: conserva la decisión original")
print("\n" + ("TODO OK" if not F else f"{F} FALLAS")); sys.exit(1 if F else 0)
