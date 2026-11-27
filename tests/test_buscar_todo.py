"""Prueba de punta a punta de «buscar todo» (V1 carpeta + V2 conversaciones con modelos) sobre un proyecto y sesiones SINTÉTICOS, en una carpeta temporal.
Necesita la instalación con modelos (scripts/buscador/preparar_profundo.py) en BUSCADOR_HOME (por defecto ~/.memoria-local); si no está, se omite. No toca tu índice real.
Uso: python3 -I tests/test_buscar_todo.py"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; PY = sys.executable
HOME_REAL = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local")
if not (HOME_REAL / "profundo" / "aislado.ok").exists(): print("OMITIDA: no hay instalación con modelos sellada en", HOME_REAL); sys.exit(0)
TMP = Path(tempfile.mkdtemp(prefix="memoria-local-todo-")); fallas = []
try:
    home = TMP / "home"; (home / "profundo").mkdir(parents=True)  # modelos y entorno compartidos (solo lectura); índices y vectores NUEVOS en la carpeta temporal
    for n in ("venv", "modelos", "manifiesto.json", "aislado.ok"): os.symlink(HOME_REAL / "profundo" / n, home / "profundo" / n)
    proyecto = TMP / "proyecto"; (proyecto / "docs").mkdir(parents=True); ses = TMP / "sesiones"; ses.mkdir()
    (proyecto / "docs/exportacion.md").write_text("# Exportación mensual\n\nLa exportación mensual genera un CSV con separador punto y coma y codificación UTF-8.\n", encoding="utf-8")
    (proyecto / "docs/receta.md").write_text("# Receta de pan\n\nFermentar doce horas en frío y hornear con vapor.\n", encoding="utf-8")
    with open(ses / "bbbbbbbb-2222-4222-8222-222222222222.jsonl", "w", encoding="utf-8") as f:
        for u, a in (("Decidimos el formato del reporte semanal: tabla con tres columnas.", "Perfecto: columnas fecha, métrica y valor; se exporta cada lunes."), ("Receta de pan de masa madre al 75 % de hidratación.", "Fermentar 12 horas en frío.")):
            f.write(json.dumps({"type": "user", "timestamp": "2026-01-12T16:00:00Z", "message": {"role": "user", "content": u}}) + "\n")
            f.write(json.dumps({"type": "assistant", "timestamp": "2026-01-12T16:00:00Z", "message": {"role": "assistant", "content": [{"type": "text", "text": a}]}}) + "\n")
    env = dict(os.environ, BUSCADOR_HOME=str(home), CLAUDE_PROJECT_DIR=str(proyecto), BUSCADOR_ZONA="UTC")
    r = subprocess.run([PY, "-I", str(REPO / "scripts/buscador/buscar_todo.py"), "ABC-123 formato del reporte semanal y la exportación mensual", "--auto", "--sesiones", str(ses), "--raiz", str(proyecto)], capture_output=True, text=True, env=env, timeout=900)
    o = r.stdout; v2 = o.split("== 📁")[0]; v1 = o.split("== 📁")[1] if "== 📁" in o else ""
    for nombre, ok in (("termina bien", r.returncode == 0), ("trae las dos secciones", "== 💬" in o and "== 📁" in o), ("V2: encuentra la sesión del formato del reporte", "bbbbbbbb" in v2), ("V1: encuentra el documento de la exportación", "docs/exportacion.md" in v1)):
        print("OK   " if ok else "FALLA", nombre); fallas.append(nombre) if not ok else None
    if fallas: print(r.stdout[-600:], r.stderr[-600:])
    r = subprocess.run([PY, "-I", str(REPO / "scripts/buscador/buscar_todo.py"), "--marca", "v1", "ABC-123"], capture_output=True, text=True, env=env)
    ok = r.returncode == 0 and "Marcada" in r.stdout; print("OK   " if ok else "FALLA", "marca de resultado y registro local"); fallas.append("marca") if not ok else None
finally:
    shutil.rmtree(TMP, ignore_errors=True)  # incluye los índices y vectores de prueba
print("\n" + ("TODO OK" if not fallas else "FALLAS: " + ", ".join(fallas))); sys.exit(1 if fallas else 0)
