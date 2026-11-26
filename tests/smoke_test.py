"""Prueba de humo SIN modelos y SIN tocar tu índice real: arma en una carpeta temporal un proyecto y tres sesiones sintéticas y comprueba
(1) el analizador de fechas, (2) la búsqueda V2 con fecha y exclusión, (3) el mapa de directivas, (4) el hook por mensaje y (5) la forma corta del índice de memoria.
Uso: python3 -I tests/smoke_test.py"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; PY = sys.executable
TMP = Path(tempfile.mkdtemp(prefix="memoria-local-smoke-")); fallas = []


def chequeo(nombre, ok, detalle=""):
    print(("OK   " if ok else "FALLA"), nombre, detalle); fallas.append(nombre) if not ok else None


def sesion(carpeta, uuid, turnos):
    with open(carpeta / f"{uuid}.jsonl", "w", encoding="utf-8") as f:
        for ts, u, a in turnos:
            f.write(json.dumps({"type": "user", "timestamp": ts, "message": {"role": "user", "content": u}}) + "\n")
            f.write(json.dumps({"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [{"type": "text", "text": a}]}}) + "\n")


try:
    proyecto = TMP / "proyecto"; shutil.copytree(REPO / "scripts", proyecto / "scripts", ignore=shutil.ignore_patterns("__pycache__")); shutil.copytree(REPO / ".context", proyecto / ".context")
    ses = TMP / "sesiones"; ses.mkdir()
    sesion(ses, "aaaaaaaa-1111-4111-8111-111111111111", [("2026-01-10T15:00:00Z", "¿Cómo configuramos el entorno de pruebas del reporte semanal?", "Usamos una variable REPORTE_ENTORNO=pruebas y una base de datos de ejemplo separada.")])
    sesion(ses, "bbbbbbbb-2222-4222-8222-222222222222", [("2026-01-12T16:00:00Z", "Decidimos el formato del reporte semanal: tabla con tres columnas.", "Perfecto: columnas fecha, métrica y valor; se envía los lunes.")])
    sesion(ses, "cccccccc-3333-4333-8333-333333333333", [("2026-01-15T17:00:00Z", "Receta de pan de masa madre con hidratación al 75 %.", "Fermentar 12 horas en frío y hornear con vapor.")])
    env = dict(os.environ, BUSCADOR_HOME=str(TMP / "home"), CLAUDE_PROJECT_DIR=str(proyecto), BUSCADOR_ZONA="UTC")

    # 1) fechas
    r = subprocess.run([PY, "-I", str(proyecto / "scripts/buscador/evaluacion/probar_fechas.py")], capture_output=True, text=True, env=env); chequeo("analizador de fechas", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
    # 2) búsqueda V2 (sin modelos)
    def buscar(*extra):
        r = subprocess.run([PY, "-I", str(proyecto / "scripts/buscador/buscar_sesiones.py"), *extra, "--sesiones", str(ses), "--solo-v2", "--sin-registro", "--json", "--hoy", "2026-01-20"], capture_output=True, text=True, env=env)
        return json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {"resultados": [], "stderr": r.stderr[-300:]}
    j = buscar("formato del reporte semanal"); top = [x["sesion"] for x in j["resultados"]]
    chequeo("búsqueda: encuentra la sesión del formato del reporte", top[:1] == ["bbbbbbbb"], str(top[:3]))
    j = buscar("el 10 de enero reporte semanal"); chequeo("búsqueda: el filtro de fecha deja solo el 10 de enero", [x["sesion"] for x in j["resultados"]] == ["aaaaaaaa"], str([x["sesion"] for x in j["resultados"]]))
    j = buscar("reporte semanal", "--excluir", "bbbbbbbb"); chequeo("búsqueda: --excluir quita una sesión", "bbbbbbbb" not in [x["sesion"] for x in j["resultados"]])
    j = buscar("pan masa madre"); chequeo("búsqueda: otra sesión distinta se encuentra por su tema", [x["sesion"] for x in j["resultados"]][:1] == ["cccccccc"])
    # 3) mapa de directivas
    D = [PY, "-I", str(proyecto / "scripts/directivas-buscador/directivas_buscador.py")]
    r = subprocess.run(D + ["mapa"], capture_output=True, text=True, env=env); mapa = (proyecto / ".context/directivas-mapa.md").read_text(encoding="utf-8") if (proyecto / ".context/directivas-mapa.md").exists() else ""
    chequeo("mapa: se genera con el núcleo y una fila por directiva", r.returncode == 0 and "## Núcleo" in mapa and "· Preguntas sobre lo hablado" in mapa, r.stdout.strip()[:100])
    # 4) hook por mensaje (una sesión por mensaje)
    def hook(msg, k):
        r = subprocess.run(D + ["hook"], input=json.dumps({"prompt": msg, "session_id": f"humo-{k}"}), capture_output=True, text=True, env=env)
        try: return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        except Exception: return ""
    t = hook("¿Qué dijimos ayer sobre el formato del reporte? No me acuerdo de lo que decidimos", 1)
    chequeo("hook: inyecta la directiva de lo hablado, con el modo y sin la procedencia", "modo base" in t and "procedencia omitida" in t and "textual:" not in t, f"{len(t)} caracteres")
    chequeo("hook: un mensaje sin relación no inyecta nada", hook("xyzzy plugh qwerty", 2) == "")
    # 5) índice de memoria en forma corta
    mem = Path.home() / ".claude/projects"  # no se toca: solo se prueba la función de normalización sobre un archivo temporal
    import importlib.util
    sp = importlib.util.spec_from_file_location("d", proyecto / "scripts/directivas-buscador/directivas_buscador.py"); d = importlib.util.module_from_spec(sp); sp.loader.exec_module(d)
    s = d.sin_procedencia("- **Regla** _(ejemplo, 2026-01-01; textual: «x (y)»)_. Detalle. _(otra nota)_")
    chequeo("la procedencia se quita al inyectar (con paréntesis dentro) y la regla se conserva", "textual:" not in s and "otra nota" not in s and "Detalle." in s and s.count("procedencia omitida") == 1, s)
finally:
    shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("TODO OK" if not fallas else "FALLAS: " + ", ".join(fallas))); sys.exit(1 if fallas else 0)
