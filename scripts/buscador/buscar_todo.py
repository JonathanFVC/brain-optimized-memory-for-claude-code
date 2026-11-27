"""Lanzador de BUSCAR TODO : corre buscar_todo_modelos.py con el Python del entorno aislado dentro de sandbox-exec (sin red a nivel de sistema); falla cerrado si no hay aislamiento.
Uso: python3.12 -I scripts/buscador/buscar_todo.py "<pregunta>" [-k 3] [--excluir UUID ...] [--urgente|--ligero] [--solo carpeta|conversaciones]
Con --auto: el enrutador (enrutar_busqueda.py) decide con las señales del pedido si buscar, en qué fuente, cuántos resultados y si es urgente; con --explica solo muestra la decisión, sin buscar."""
import datetime, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent; HOME = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local"); PROF = HOME / "profundo"
sys.path.insert(0, str(AQUI)); import buscar_sesiones as bs  # solo para reutilizar _aislante(); no corre nada


DATOS = HOME / "uso"; USO = DATOS / "uso_enrutador.jsonl"; MARCAS = DATOS / "uso_enrutador_marcas.jsonl"; ULTIMA = DATOS / "uso_enrutador_ultima.json"; INFORME = DATOS / "informe_criterios.md"
# REGISTRO LOCAL en segundo plano: una fila por búsqueda con la decisión del enrutador y los IDENTIFICADORES de lo mostrado; nunca el texto del mensaje ni el de las conversaciones.


def _anexar(ruta, obj):
    ruta.parent.mkdir(parents=True, exist_ok=True); nuevo = not ruta.exists()
    with open(ruta, "a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    if nuevo: os.chmod(ruta, 0o600)


def _filas(ruta): return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()] if ruta.exists() else []


def resultados(out):
    res, sec = [], None
    for l in out.splitlines():
        if l.startswith("== 💬"): sec = "v2"
        elif l.startswith("== 📁"): sec = "v1"
        m = re.match(r"\s*\d+\. (.+)", l)
        if not m: continue
        r2 = re.match(r"\[([0-9a-f]{8}:L\d+)\]", m.group(1))
        if r2 and sec in (None, "v2"): res.append({"f": "v2", "ref": r2.group(1)}); continue
        r1 = re.match(r"(\S+?:L\d+(?:-L\d+)?)", m.group(1))
        if r1: res.append({"f": "v1", "ref": r1.group(1)})
    return res


def registrar(msg, d, out=""):
    try:
        ahora = datetime.datetime.now(); cid = ahora.strftime("%Y%m%dT%H%M%S") + "-" + hashlib.sha1((msg + ahora.isoformat()).encode()).hexdigest()[:4]
        _anexar(USO, {"id": cid, "ts": ahora.isoformat(timespec="seconds"), "buscar": d["buscar"], "fuente": d["fuente"], "k": d["k"], "rutas": d["rutas"], "urgente": d["urgente"], "refs": d["refs"], "motivo": d["motivo"],
                      "tokens": d["tokens_aprox"], "largo": len(msg), "lineas": msg.count("\n") + 1, "resultados": resultados(out)})
        ULTIMA.write_text(json.dumps({"id": cid, "fuente": d["fuente"]}), encoding="utf-8"); os.chmod(ULTIMA, 0o600)
        if len(_filas(USO)) % 25 == 0: informe()  # informe automático cada 25 mensajes
    except OSError: pass  # el registro nunca debe romper la búsqueda


def marcar(marca, etiqueta=""):
    if marca not in ("v1", "v2", "ambas", "ninguna"): return "Marca inválida: usa v1, v2, ambas o ninguna (qué fuente aportó a la tarea)."
    if not ULTIMA.exists(): return "No hay una búsqueda reciente que marcar."
    u = json.loads(ULTIMA.read_text(encoding="utf-8")); _anexar(MARCAS, {"id": u["id"], "marca": marca, "tarea": etiqueta[:80], "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    return f"Marcada la búsqueda {u['id']}{' (' + etiqueta + ')' if etiqueta else ''}: aportó «{marca}» (el enrutador eligió: {u['fuente'] or 'no buscar'})."


def informe():
    from collections import Counter, defaultdict
    f = [x for x in _filas(USO)]; mk = {m["id"]: m["marca"] for m in _filas(MARCAS)}
    if not f: return "Sin registro todavía (se llena con --auto)."
    L = [f"# Informe de criterios del enrutador _(generado {time.strftime('%Y-%m-%d %H:%M')}; solo señales, sin texto de mensajes)_", ""]
    por = Counter((x["fuente"] or "no busca") for x in f); tok = sum(x["tokens"] for x in f)
    L += [f"- **{len(f)} decisiones** ({f[0]['ts'][:16]} → {f[-1]['ts'][:16]}) · por fuente: {dict(por)} · urgentes: {sum(x['urgente'] for x in f)}",
          f"- Tokens estimados {tok} (≈ {tok // len(f)} por mensaje) frente a {1040 * len(f)} si siempre se buscara en las dos con 3 resultados", f"- Con marca de resultado: {sum(1 for x in f if x['id'] in mk)} de {len(f)}", ""]
    cruce = defaultdict(Counter)
    for x in f:
        if x["buscar"]: cruce[x["fuente"]][mk.get(x["id"], "sin marca")] += 1
    L += ["## Decisión del enrutador × fuente que sí aportó (marca)", "| decidió | v1 | v2 | ambas | ninguna | sin marca |", "|---|---|---|---|---|---|"]
    for fu, c in cruce.items(): L.append(f"| {fu} | " + " | ".join(str(c.get(k, 0)) for k in ("v1", "v2", "ambas", "ninguna", "sin marca")) + " |")
    fallos = [x for x in f if x["id"] in mk and ((x["fuente"] == "conversaciones" and mk[x["id"]] in ("v1", "ambas")) or (x["fuente"] == "carpeta" and mk[x["id"]] in ("v2", "ambas")))]
    sobra = [x for x in f if x["id"] in mk and x["fuente"] == "ambas" and mk[x["id"]] in ("v1", "v2")]
    L += ["", f"- **Faltó una fuente** (el enrutador eligió una sola y la otra aportaba): {len(fallos)}", f"- **Sobró una fuente** (se buscó en las dos y solo una aportó; ahorro posible): {len(sobra)}",
          f"- **Búsqueda sin aporte** (marca «ninguna»): {sum(1 for x in f if mk.get(x['id']) == 'ninguna')}", ""]
    cam = 0
    for a, b in zip(f, f[1:]):
        if a["buscar"] and b["buscar"] and a["fuente"] in ("conversaciones", "carpeta") and b["fuente"] in ("ambas", "conversaciones", "carpeta") and b["fuente"] != a["fuente"] and datetime.datetime.fromisoformat(b["ts"]) - datetime.datetime.fromisoformat(a["ts"]) < datetime.timedelta(minutes=10): cam += 1
    L += [f"- **Cambio de fuente en menos de 10 min** (señal implícita de que la primera no bastó): {cam}", "", "## Motivos (≥ 3 usos) y qué marcaron", "| motivo | usos | marcas |", "|---|---|---|"]
    for mo, n in Counter(x["motivo"] for x in f).most_common():
        if n >= 3: L.append(f"| {mo} | {n} | {dict(Counter(mk[x['id']] for x in f if x['motivo'] == mo and x['id'] in mk)) or '—'} |")
    tar = [m for m in _filas(MARCAS) if m.get("tarea")]; por_id = {x["id"]: x for x in f}
    if tar:
        L += ["", "## Últimas tareas cerradas (qué se usó en cada una)", "| tarea | el enrutador eligió | aportó | motivo |", "|---|---|---|---|"]
        for m in tar[-15:]: x = por_id.get(m["id"], {}); L.append(f"| {m['tarea']} | {x.get('fuente') or '—'} | {m['marca']} | {x.get('motivo', '—')} |")
    L += ["", "## Cómo leerlo", "- Una regla se propone cuando un motivo tiene ≥ 8 usos con marca y ≥ 80 % apunta a la misma fuente; se prueba contra los 288 mensajes de prueba antes de aplicarla y solo se aplica con orden del usuario.",
          "- «Sobró una fuente» repetido en un mismo motivo = candidato a mandar ese motivo a una sola fuente (ahorro); «Faltó una fuente» = candidato a mandarlo a las dos."]
    INFORME.write_text("\n".join(L) + "\n", encoding="utf-8"); os.chmod(INFORME, 0o600); return "\n".join(L)


def ejecutar(cmd, env=None, msg=None, d=None):
    r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, text=True); sys.stdout.write(r.stdout)
    if d is not None and r.returncode == 0: registrar(msg, d, r.stdout)
    return r.returncode


def main():
    args = sys.argv[1:]
    msg = d = None
    if args[:1] == ["--informe"]: print(informe()); return 0
    if args[:1] == ["--marca"]: print(marcar(args[1] if len(args) > 1 else "", " ".join(args[2:]))); return 0
    if args[:1] == ["--borrar-uso-enrutador"]:
        for x in (USO, MARCAS, ULTIMA, INFORME): x.unlink(missing_ok=True)
        print("Registro del enrutador borrado."); return 0
    if ("--auto" in args or "--explica" in args) and args and not args[0].startswith("-"):
        import enrutar_busqueda as E
        msg, resto = args[0], [x for x in args[1:] if x not in ("--auto", "--explica")]; d = E.decidir(msg)
        if "--explica" in args: print(json.dumps(d, ensure_ascii=False, indent=1)); return 0
        if not d["buscar"]:
            registrar(msg, d); print(f"No hace falta buscar: {d['motivo']}.")
            if d.get("siguiente"): print("→ " + d["siguiente"])
            return 0
        print(f"[enrutador] {d['fuente']} · {d['k']} resultados{' · rutas' if d['rutas'] else ''}{' · urgente' if d['urgente'] else ''} · ≈ {d['tokens_aprox']} tokens · {d['motivo']}", file=sys.stderr)
        if d["rutas"]: return ejecutar([sys.executable, "-I", str(AQUI / "buscar.py"), d.get("consulta", msg), "--rutas", "-k", "5"], msg=msg, d=d)
        args = [d.get("consulta", msg), "-k", str(d["k"])] + ([] if d["fuente"] == "ambas" else ["--solo", d["fuente"]]) + (["--urgente"] if d["urgente"] else []) + [x for x in resto if x not in ("--urgente", "--ligero")]
    py = PROF / "venv" / "bin" / "python"
    if not py.exists(): print("[ALTO] falta el entorno de modelos (~/.memoria-local/profundo/venv); prepáralo con preparar_profundo.py.", file=sys.stderr); return 2
    aislar = bs._aislante()
    if aislar is None and not os.environ.get("BUSCADOR_PERMITIR_SIN_SANDBOX"):
        print("[ALTO] no hay forma de aislar la red a nivel de sistema: por seguridad no se corren los modelos.", file=sys.stderr); return 4
    return ejecutar((aislar or []) + [str(py), "-I", str(AQUI / "buscar_todo_modelos.py")] + args, env=dict(os.environ, BUSCADOR_SESIONES_EN_PROFUNDO="1"), msg=msg, d=d)


if __name__ == "__main__":
    sys.exit(main())
