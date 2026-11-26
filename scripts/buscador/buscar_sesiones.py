"""Buscador de CONVERSACIONES pasadas de Claude Code. 100 % local: V2 usa solo la biblioteca estándar de Python + SQLite FTS5; los modos con modelos corren aparte y sin red.

Qué hace: indexa los turnos (mensaje del usuario + texto de Claude) de las sesiones .jsonl de Claude Code y los busca con BM25 sobre palabras fusionado (RRF) con BM25 sobre prefijos de
5 letras (une variantes como transcripción/transcribir) y, si la pregunta trae una fecha en español («ayer», «hace 5 días», «el 12 de noviembre», «la semana pasada»…), filtra por ese día.

Uso:  python3 -I buscar_sesiones.py "¿qué decidimos del micrófono?" [-k 5] [--sesiones DIR_O_GLOB] [--db ARCHIVO.db]
      [--excluir UUID ...] [--hoy AAAA-MM-DD] [--reindex] [--sin-sync] [--json] [--stats] [--modo MODO] [--ligero|--profundo|--maximo|--ultraligero]
Cuatro modos. El modo BASE (archivo `modo` en la carpeta de datos; se cambia con `--modo` o con el icono de la barra de menú de macOS) lo usa toda búsqueda sin bandera; por defecto MÁXIMO si está instalado y, si no, PROFUNDO. Una bandera explícita manda sobre el modo base.
ULTRA LIGERO (`--ultraligero` o `--solo-v2`) = solo BM25, sin modelos (≈ 0.1 s; menor precisión; MRR 0.47). LIGERO (`--ligero`) = V2 + reordenador gte-multilingual-reranker-base sobre 20 candidatos (≈ 3–7 s; MRR 0.60). PROFUNDO (`--profundo`) = además vectores
multilingual-e5-small (≈ 5–9 s; MRR 0.63; gana en preguntas parafraseadas o vagas). MÁXIMO (`--maximo`) = profundo + Qwen3-Reranker-0.6B reordena los 5 mejores y se promedia con gte (≈ 7–12 s; MRR 0.66; el mejor medido). Los modos con modelos corren en un programa aparte
(buscar_profundo.py) en un entorno aislado y SIN RED. Si el modo con modelos no está instalado, se avisa y se usa V2. Instalación: scripts/buscador/preparar_profundo.py (Ligero y Profundo) y scripts/buscador/preparar_maximo.py (Máximo, opcional).
Privacidad: el índice vive fuera del proyecto (por defecto ~/.memoria-local/sesiones.db; cambiar con BUSCADOR_HOME, carpeta 700, archivo 600) y guarda TODO sin enmascarar, contraseñas incluidas: es una copia sensible de tus
conversaciones; no la copies ni la subas. --ocultar enmascara los secretos solo AL MOSTRAR. Nada sale del equipo.
Resultado = mapa: se confirma abriendo la sesión (uuid:línea) y el estado vivo se verifica en vivo; puede traer decisiones ya superadas (mira la fecha)."""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())  # proyecto cuyas sesiones se buscan por defecto
BASE = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local")  # índice, modelos y registro de uso (fuera del proyecto)
DB_DEF = BASE / "sesiones.db"
SES_DEF = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))  # sesiones de ESTE proyecto; con --sesiones se da otra carpeta o un glob (p. ej. ~/.claude/projects/*)
VERSION = "7"
CAP_TEXTO = 6000
INCLUIR_HERR = True  # incluye entradas (SQL, comandos, ediciones) y resultados de herramientas de cada turno (se decide con --herramientas si|no)
CAP_HERR, CAP_HERR_TURNO, CAP_RES = 1500, 8000, 600
METODO = None  # etiqueta del registro de uso; buscar_profundo.py la cambia
PROF = BASE / "profundo"  # entorno, modelos y vectores del modo --profundo (fuera del proyecto, carpeta 700)
MODO_ARCHIVO = Path(os.environ.get("BUSCADOR_MODO_ARCHIVO", str(BASE / "modo")))  # modo base elegido en el icono de la barra de menú o con --modo
MODOS = ("ultraligero", "ligero", "profundo", "maximo")  # nombres de cara al usuario; «v2» se acepta como sinónimo de ultraligero
STOP = set("""a al algo ante con contra cual cuando de del desde donde el ella ellos en entre es esa ese eso esta este esto
la las le les lo los me mi mis muy no nos o para pero por que se si sin sobre su sus te tu un una uno unos unas y ya
como cuales cuantos hay hace hacer hacemos ver tiene tienen qué cómo cuál documentos documento archivo archivos script scripts""".split())
SIGLAS = {s for s in os.environ.get("BUSCADOR_SIGLAS", "").lower().replace(" ", "").split(",") if s}  # siglas de 2 letras que cuentan como palabra (por defecto ninguna; p. ej. BUSCADOR_SIGLAS=ci,qa)
CUE_HERR = re.compile(r"\b(query|queries|consulta|consultas|sql|select|comando|comandos|script|corrimos|ejecutamos|ejecute|ejecuto|alter|insert|grant|bash|terminal)\b")
TK = re.compile(r"[a-z]{2,5}-\d{2,5}|[a-z0-9]{2,}")
REM = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PEGADO = re.compile(r"</?pasted_content[^>]*>")
RUIDO = ("<command-", "<local-command", "[Request interrupted", "Caveat:", "<bash-", "<task-notification", "[SYSTEM NOTIFICATION")
SECRETOS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)"), "***CLAVE PRIVADA***"),
    (re.compile(r"(://[^/\s:@]+:)[^@\s/]{3,}(@)"), r"\1***\2"),
    (re.compile(r"(xox[bp]-|lin_api_|ghp_|sk-)[A-Za-z0-9_-]{16,}"), r"\1***"),
    (re.compile(r"(?i)\b(password|passwd|pwd|contrase[nñ]a|secret|api[_-]?key)(\"?\s*[:=]\s*\"?|\s+es\s+)[^\s\"',;|`)<]{4,}"), r"\1\2***"),
    (re.compile(r"(?i)\b(BY|IDENTIFIED BY)\s+'[^']{6,}'"), r"\1 '***'"),
    # valor entre comillas inversas cerca de las palabras contraseña / clave / token / secreto (p. ej. «Nueva contraseña de 15 caracteres: `…`»)
    (re.compile(r"(?i)(\b(?:contrase[nñ]a|password|clave|token|secret|secreto)\b[^\n`]{0,120}`)([^`\n]{6,80})(`)"), r"\1***\3"),
    # cadena de aspecto aleatorio (12 a 40 letras y números con minúscula, mayúscula y dígito): contraseñas generadas sin etiqueta cerca
    (re.compile(r"\b(?=[A-Za-z0-9]*[a-z])(?=[A-Za-z0-9]*[A-Z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{12,40}\b"), "***"),
]


def enmascarar(t):
    for r, s in SECRETOS:
        t = r.sub(s, t)
    return t


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def palabras(s):
    return [w for w in TK.findall(norm(s)) if "-" in w or (len(w) >= 3 and w not in STOP) or w in SIGLAS]


def pref(w):
    return w[:5] if len(w) >= 6 and "-" not in w else w


# ---------------------------------------------------------------- fechas en español
MES = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
DIA = {d: i for i, d in enumerate("lunes martes miercoles jueves viernes sabado domingo".split())}


def fechas_es(q, hoy):
    """(inicio, fin, pregunta sin la frase de fecha) o None. Referencia: hoy."""
    s = norm(q)
    D, td = datetime.date, datetime.timedelta

    def fin(m, a, b):
        return a, b, (s[:m.start()] + " " + s[m.end():]).strip()
    mr = lambda p: re.search(p, s)
    if m := mr(r"\bhace (\d+) dias?\b"):
        d = hoy - td(int(m.group(1))); return fin(m, d, d)
    if m := mr(r"\b(antier|anteayer)\b"):
        d = hoy - td(2); return fin(m, d, d)
    if m := mr(r"\bayer\b"):
        d = hoy - td(1); return fin(m, d, d)
    if m := mr(r"\bla semana pasada\b"):
        lu = hoy - td(hoy.weekday() + 7); return fin(m, lu, lu + td(6))
    if m := mr(r"\besta semana\b"):
        return fin(m, hoy - td(hoy.weekday()), hoy)
    if m := mr(r"\bel mes pasado\b"):
        u = hoy.replace(day=1) - td(1); return fin(m, u.replace(day=1), u)
    if m := mr(r"\b(20\d\d)-(\d\d)-(\d\d)\b"):
        try:
            d = D(int(m.group(1)), int(m.group(2)), int(m.group(3))); return fin(m, d, d)
        except ValueError:
            return None
    if m := mr(r"\b(\d{1,2}) de (" + "|".join(MES) + r")(?: de (\d{4}))?\b"):
        try:
            d = D(int(m.group(3) or hoy.year), MES[m.group(2)], int(m.group(1))); return fin(m, d, d)
        except ValueError:
            return None
    if m := mr(r"\b(?:el )?(" + "|".join(DIA) + r")(?: pasado)?\b"):
        d = hoy - td((hoy.weekday() - DIA[m.group(1)]) % 7 or 7); return fin(m, d, d)
    if m := mr(r"\ben (" + "|".join(MES) + r")\b"):
        a = D(hoy.year if MES[m.group(1)] <= hoy.month else hoy.year - 1, MES[m.group(1)], 1)
        b = (a.replace(day=28) + td(4)).replace(day=1) - td(1); return fin(m, a, b)
    if m := mr(r"\bhoy\b"):  # al final (2026-11-25): «hoy» suele ser la referencia del presente («el mes pasado hablamos… ¿cómo lo cambiaría hoy?») y no debe tapar otra fecha
        return fin(m, hoy, hoy)
    return None


# ---------------------------------------------------------------- lectura de sesiones
def _textos(c):
    if isinstance(c, str):
        return c
    return "\n".join(b["text"] for b in (c or []) if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))


def _limpio(t):
    return PEGADO.sub("", REM.sub("", t)).strip()


def titulo_de(ruta):
    t = ""
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        for l in f:
            if "custom-title" in l or "agent-name" in l:
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                t = d.get("customTitle") or d.get("agentName") or t
    return t or "(sin título)"


def _herramienta(b):
    """Texto buscable de una llamada a herramienta (SQL, comando, ruta editada) o de su resultado (recortado)."""
    t = b.get("type")
    if t == "tool_use":
        i = b.get("input") or {}
        nombre = b.get("name", "?")
        txt = ""
        if isinstance(i, dict):
            txt = str(i.get("command") or i.get("queryText") or i.get("query") or i.get("file_path") or i.get("path") or "")
            if nombre in ("Edit", "Write", "MultiEdit"):
                txt += " " + str(i.get("new_string") or i.get("content") or "")[:400]
        if not txt.strip():
            txt = json.dumps(i, ensure_ascii=False)
        return f"[{nombre}] {txt}"[:CAP_HERR]
    if t == "tool_result":
        c = b.get("content")
        s_ = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
        s_ = s_.strip()
        return ("→ " + s_[:CAP_RES]) if s_ else None
    return None


def turnos_de(ruta):
    """[{n, n2, ts, u, a}] un turno = mensaje del usuario + texto de Claude hasta el siguiente mensaje del usuario."""
    out, act = [], None
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        for n, l in enumerate(f, 1):
            if '"user"' not in l and '"assistant"' not in l:
                continue
            try:
                d = json.loads(l)
            except ValueError:
                continue
            tp, m = d.get("type"), d.get("message")
            if tp not in ("user", "assistant") or d.get("isSidechain") or not isinstance(m, dict):
                continue
            if INCLUIR_HERR and act is not None and isinstance(m.get("content"), list):
                for b in m["content"]:
                    x = _herramienta(b) if isinstance(b, dict) else None
                    if x:
                        act["h"].append(x)
            t = _limpio(_textos(m.get("content")))
            if tp == "user":
                if d.get("isCompactSummary") or d.get("isMeta") or not t or t.startswith(RUIDO):
                    continue
                if act:
                    out.append(act)
                act = {"n": n, "n2": n, "ts": d.get("timestamp", ""), "u": t[:CAP_TEXTO], "a": [], "h": []}
            elif act and t:
                act["a"].append(t); act["n2"] = n
    if act:
        out.append(act)
    return out


def dia_local(ts):
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return "0000-00-00"
    try:
        from zoneinfo import ZoneInfo
        z = os.environ.get("BUSCADOR_ZONA")  # p. ej. America/Bogota; por defecto, la zona del sistema
        return (dt.astimezone(ZoneInfo(z)) if z else dt.astimezone()).date().isoformat()
    except Exception:
        return dt.date().isoformat()


# ---------------------------------------------------------------- índice
def abrir(db):
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(db.parent, 0o700)
    except OSError:
        pass
    con = sqlite3.connect(str(db))
    try:
        os.chmod(db, 0o600)
    except OSError:
        pass
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    v = con.execute("SELECT v FROM meta WHERE k='version'").fetchone()
    modo = "si" if INCLUIR_HERR else "no"
    mh = con.execute("SELECT v FROM meta WHERE k='herramientas'").fetchone()
    if not v or v[0] != VERSION or not mh or mh[0] != modo:
        con.executescript("DROP TABLE IF EXISTS archivos; DROP TABLE IF EXISTS turnos; DROP TABLE IF EXISTS t_pal; DROP TABLE IF EXISTS t_pref; DROP TABLE IF EXISTS h_pal; DROP TABLE IF EXISTS h_pref;")
        con.execute("INSERT OR REPLACE INTO meta VALUES('version',?)", (VERSION,))
        con.execute("INSERT OR REPLACE INTO meta VALUES('herramientas',?)", (modo,))
    con.executescript("""
    CREATE TABLE IF NOT EXISTS archivos(uuid TEXT PRIMARY KEY, size INT, mtime_ns INT);
    CREATE TABLE IF NOT EXISTS turnos(id INTEGER PRIMARY KEY, uuid TEXT, titulo TEXT, l1 INT, l2 INT, ts TEXT, dia TEXT, usuario TEXT, asistente TEXT, herramientas TEXT);
    CREATE INDEX IF NOT EXISTS i_turnos_uuid ON turnos(uuid);
    CREATE INDEX IF NOT EXISTS i_turnos_dia ON turnos(dia);
    CREATE VIRTUAL TABLE IF NOT EXISTS t_pal USING fts5(heading, usuario, asistente, tokenize='unicode61');
    CREATE VIRTUAL TABLE IF NOT EXISTS t_pref USING fts5(heading, usuario, asistente, tokenize='unicode61');
    CREATE VIRTUAL TABLE IF NOT EXISTS h_pal USING fts5(texto, tokenize='unicode61');
    CREATE VIRTUAL TABLE IF NOT EXISTS h_pref USING fts5(texto, tokenize='unicode61');
    """)
    return con


def _cont(texto):
    """Solo palabras de contenido (sin acentos, sin palabras vacías): así BM25 mide la longitud del turno como lo hacen las pruebas."""
    return " ".join(palabras(texto))


def _prefijos(texto):
    return " ".join(pref(w) for w in palabras(texto))


def borrar(con, uuid):
    ids = [r[0] for r in con.execute("SELECT id FROM turnos WHERE uuid=?", (uuid,))]
    for i in ids:
        for t_ in ("t_pal", "t_pref", "h_pal", "h_pref"):
            con.execute(f"DELETE FROM {t_} WHERE rowid=?", (i,))
    con.execute("DELETE FROM turnos WHERE uuid=?", (uuid,)); con.execute("DELETE FROM archivos WHERE uuid=?", (uuid,))


def reindexar(con, ruta):
    uuid = ruta.stem
    borrar(con, uuid)
    titulo = titulo_de(ruta); n = 0
    for t in turnos_de(ruta):
        u, a = t["u"], "\n".join(t["a"])[:CAP_TEXTO]; dia = dia_local(t["ts"]); h_ = "\n".join(t["h"])[:CAP_HERR_TURNO]
        cur = con.execute("INSERT INTO turnos(uuid,titulo,l1,l2,ts,dia,usuario,asistente,herramientas) VALUES(?,?,?,?,?,?,?,?,?)", (uuid, titulo, t["n"], t["n2"], t["ts"], dia, u, a, h_))
        h = f"{titulo} · {dia}"
        con.execute("INSERT INTO t_pal(rowid,heading,usuario,asistente) VALUES(?,?,?,?)", (cur.lastrowid, _cont(h), _cont(u), _cont(a)))
        con.execute("INSERT INTO t_pref(rowid,heading,usuario,asistente) VALUES(?,?,?,?)", (cur.lastrowid, _prefijos(h), _prefijos(u), _prefijos(a)))
        if h_:  # las herramientas van en tablas APARTE: así no cambian la longitud de la fila ni el ranking de la búsqueda normal
            con.execute("INSERT INTO h_pal(rowid,texto) VALUES(?,?)", (cur.lastrowid, _cont(h_)))
            con.execute("INSERT INTO h_pref(rowid,texto) VALUES(?,?)", (cur.lastrowid, _prefijos(h_)))
        n += 1
    st = ruta.stat()
    con.execute("INSERT OR REPLACE INTO archivos VALUES(?,?,?)", (uuid, st.st_size, st.st_mtime_ns))
    return n


def listar_sesiones(spec):
    spec = str(spec)
    if os.path.isdir(spec):
        spec = os.path.join(spec, "*.jsonl")
    return sorted(Path(p) for p in glob.glob(os.path.expanduser(spec)))


def sincronizar(con, spec, excluir=(), forzar=False):
    previos = {r[0]: (r[1], r[2]) for r in con.execute("SELECT uuid,size,mtime_ns FROM archivos")}
    vistos, nuevos = set(), 0
    for p in listar_sesiones(spec):
        if any(p.stem.startswith(x) for x in excluir):
            continue
        vistos.add(p.stem); st = p.stat()
        if not forzar and previos.get(p.stem) == (st.st_size, st.st_mtime_ns):
            continue
        reindexar(con, p); nuevos += 1
        con.commit()
    for u in set(previos) - vistos:
        borrar(con, u)
    con.commit()
    return nuevos


# ---------------------------------------------------------------- búsqueda
def _lista(con, tabla, expr, rango, k=100):
    sql = f"SELECT rowid FROM {tabla} WHERE {tabla} MATCH ? " + ("AND rowid IN (SELECT id FROM turnos WHERE dia BETWEEN ? AND ?) " if rango else "") + f"ORDER BY bm25({tabla}, 6.0, 1.0, 1.0) LIMIT ?"
    par = [expr] + ([rango[0].isoformat(), rango[1].isoformat()] if rango else []) + [k]
    try:
        return [r[0] for r in con.execute(sql, par)]
    except sqlite3.OperationalError:
        return []


def _lista_h(con, tabla, expr, rango, k=100):
    """Búsqueda en el texto de herramientas (SQL, comandos, salidas): tablas h_pal y h_pref."""
    sql = f"SELECT rowid FROM {tabla} WHERE {tabla} MATCH ? " + ("AND rowid IN (SELECT id FROM turnos WHERE dia BETWEEN ? AND ?) " if rango else "") + f"ORDER BY bm25({tabla}) LIMIT ?"
    par = [expr] + ([rango[0].isoformat(), rango[1].isoformat()] if rango else []) + [k]
    try:
        return [r[0] for r in con.execute(sql, par)]
    except sqlite3.OperationalError:
        return []


def _rrf(*listas, k=60):
    sc = defaultdict(float)
    for L in listas:
        for r, i in enumerate(L):
            sc[i] += 1 / (k + r)
    return sorted(sc, key=lambda i: -sc[i])


def _fragmento(texto, terminos, ancho=450):
    plano = norm(texto)
    pos = min([p for p in (plano.find(t) for t in terminos) if p >= 0] or [0])
    ini = max(0, pos - 80)
    return re.sub(r"\s+", " ", texto[ini:ini + ancho]).strip()


def buscar(con, pregunta, k=5, hoy=None, usar_fecha=True, tope_sesion=2, ocultar=False, herr=None):
    """Devuelve {'resultados': [...], 'filtro_fecha': (ini, fin) | None, 'terminos': [...]}."""
    hoy = hoy or datetime.date.today()
    rango, q = None, pregunta
    if usar_fecha:
        f = fechas_es(pregunta, hoy)
        if f:
            rango, q = (f[0], f[1]), f[2]
    terminos = list(dict.fromkeys(palabras(q)))
    if not terminos:
        return {"resultados": [], "filtro_fecha": rango, "terminos": []}
    herr = bool(CUE_HERR.search(norm(pregunta))) if herr is None else herr  # preguntas de SQL o comandos: se agregan las listas del texto de herramientas
    ex_p = " OR ".join(f'"{t}"' for t in terminos); ex_f = " OR ".join(f'"{t}"' for t in dict.fromkeys(pref(t) for t in terminos))

    def listas(rg):
        return (_lista(con, "t_pal", ex_p, rg), _lista(con, "t_pref", ex_f, rg),
                _lista_h(con, "h_pal", ex_p, rg) if herr else [], _lista_h(con, "h_pref", ex_f, rg) if herr else [])
    L4 = listas(rango)
    if rango and not any(L4):  # sin nada ese día: se repite sin filtro y se avisa
        L4 = listas(None); rango = None
    out, vs, vistos = [], defaultdict(int), {}
    for i in _rrf(*L4):
        r = con.execute("SELECT uuid,titulo,l1,l2,ts,dia,usuario,asistente,herramientas FROM turnos WHERE id=?", (i,)).fetchone()
        if not r or vs[r[0]] >= tope_sesion:
            continue
        clave = norm(r[6])[:200]  # el mismo mensaje en sesiones ramificadas: se une en un solo resultado
        if clave in vistos:
            vistos[clave]["tambien_en"].append(r[0][:8])
            continue
        vs[r[0]] += 1
        texto = "USUARIO: " + r[6] + "\nCLAUDE: " + r[7] + ("\nHERRAMIENTAS: " + r[8] if r[8] else "")
        pres = set(palabras(texto)); cob = sum(1 for t in terminos if t in pres)
        nivel = "alta" if cob >= 0.7 * len(terminos) else ("media" if cob >= 0.4 * len(terminos) else "baja")
        out.append({"id": i, "sesion": r[0][:8], "uuid": r[0], "linea": r[2], "linea_fin": r[3], "fecha": r[5], "titulo": r[1], "confianza": nivel,
                    "cobertura": f"{cob}/{len(terminos)}", "fragmento": (enmascarar if ocultar else (lambda t: t))(_fragmento(texto, terminos)), "tambien_en": []})
        vistos[clave] = out[-1]
        if len(out) >= k:
            break
    return {"resultados": out, "filtro_fecha": rango, "terminos": terminos}


# ---------------------------------------------------------------- registro de uso (fase 2, local)
USO_DIR = Path(os.environ.get("BUSCADOR_SESIONES_USO", str(BASE / "uso")))


def _uso_dir():
    USO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(USO_DIR, 0o700)
    except OSError:
        pass
    return USO_DIR


def _escribir(nombre, texto, modo):
    p = _uso_dir() / nombre
    nuevo = not p.exists()
    with open(p, modo, encoding="utf-8") as f:
        f.write(texto)
    if nuevo:
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass


def _leer(nombre):
    p = _uso_dir() / nombre
    if not p.exists():
        return []
    out = []
    for l in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def registrar_consulta(pregunta, r, k):
    """Guarda la consulta (secretos enmascarados) y los IDENTIFICADORES de lo mostrado (sesión y línea), nunca el texto de las conversaciones."""
    ahora = datetime.datetime.now().astimezone()
    cid = ahora.strftime("%Y%m%dT%H%M%S") + "-" + hashlib.sha1((pregunta + ahora.isoformat()).encode()).hexdigest()[:4]
    res = [{"pos": n, "uuid": x["uuid"], "linea": x["linea"], "confianza": x["confianza"]} for n, x in enumerate(r["resultados"], 1)]
    reg = {"id": cid, "ts": ahora.isoformat(timespec="seconds"), "metodo": METODO or ("buscar_sesiones v" + VERSION), "consulta": pregunta[:300],
           "filtro_fecha": [str(x) for x in r["filtro_fecha"]] if r["filtro_fecha"] else None, "k": k, "resultados": res}
    _escribir("consultas.jsonl", json.dumps(reg, ensure_ascii=False) + "\n", "a")
    _escribir("ultima.json", json.dumps({"id": cid, "resultados": res}), "w")
    return cid


def registrar_marca(pos, util, cid=None):
    cons = None
    if cid is None:
        p = _uso_dir() / "ultima.json"
        cons = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    else:
        cons = next((c for c in _leer("consultas.jsonl") if c["id"] == cid), None)
    if not cons:
        return "No hay consulta registrada" + (f" con id {cid}" if cid else "") + "."
    x = next((r for r in cons["resultados"] if r["pos"] == pos), None)
    if not x:
        return f"La consulta {cons['id']} no tiene un resultado en la posición {pos}."
    _escribir("marcas.jsonl", json.dumps({"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "id": cons["id"], "pos": pos,
                                          "uuid": x["uuid"], "linea": x["linea"], "util": util}, ensure_ascii=False) + "\n", "a")
    return f"Marcado como {'útil' if util else 'no útil'}: consulta {cons['id']}, resultado {pos} ({x['uuid'][:8]}:L{x['linea']})."


def uso_stats():
    cs, ms = _leer("consultas.jsonl"), _leer("marcas.jsonl")
    if not cs:
        return "Sin consultas registradas todavía."
    marc = {m["id"] for m in ms}; ut = {m["id"] for m in ms if m["util"]}
    pos = sorted(m["pos"] for m in ms if m["util"])
    pm = {}
    for c in cs:
        mes = pm.setdefault(c["ts"][:7], [0, 0, 0]); mes[0] += 1; mes[1] += c["id"] in marc; mes[2] += c["id"] in ut
    lin = [f"{len(cs)} consultas · {len(marc)} con marca · {len(ut)} con al menos un fragmento útil"
           + (f" → tasa de fragmento útil en el top 5: {len(ut)/len(marc):.0%} (de las marcadas)" if marc else "")]
    if pos:
        lin.append("posición de los fragmentos útiles: " + ", ".join(f"{p}.º ×{pos.count(p)}" for p in sorted(set(pos))))
    lin += [f"  {m}: {a} consultas · {b} marcadas · {c} con útil" for m, (a, b, c) in sorted(pm.items())]
    return "\n".join(lin) + f"\n(registro en {USO_DIR})"


def borrar_uso():
    n = 0
    for nombre in ("consultas.jsonl", "marcas.jsonl", "ultima.json"):
        p = USO_DIR / nombre
        if p.exists():
            p.unlink(); n += 1
    return f"Registro de uso borrado ({n} archivos)."


def _aislante():
    """Comando que antepone un aislamiento de RED del sistema (sin red para el hijo y sus procesos): sandbox-exec en macOS; unshare o bwrap en Linux (no probado en Linux). None si no hay."""
    import shutil
    if os.path.exists("/usr/bin/sandbox-exec"):
        return ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    if shutil.which("unshare"):
        return [shutil.which("unshare"), "-rn", "--"]
    if shutil.which("bwrap"):
        return [shutil.which("bwrap"), "--bind", "/", "/", "--dev-bind", "/dev", "/dev", "--unshare-net", "--"]
    return None


def modo_base():
    """Modo base elegido (icono de la barra de menú o --modo): ultraligero, ligero, profundo o maximo. Sin archivo o con un valor raro: maximo."""
    try: v = MODO_ARCHIVO.read_text(encoding="utf-8").strip().lower()
    except OSError: v = ""
    v = "ultraligero" if v == "v2" else v
    return v if v in MODOS else "maximo"


def guardar_modo(v):
    MODO_ARCHIVO.parent.mkdir(parents=True, exist_ok=True); tmp = MODO_ARCHIVO.with_name(MODO_ARCHIVO.name + ".tmp"); tmp.write_text(v + "\n", encoding="utf-8"); os.replace(tmp, MODO_ARCHIVO)


def lanzar_profundo(modo="--profundo"):
    """--profundo: corre buscar_profundo.py con el Python del entorno aislado, dentro de sandbox-exec sin red (capa de sistema; las otras dos capas, archivos y código, van dentro del programa)."""
    if os.environ.get("BUSCADOR_SESIONES_EN_PROFUNDO"):  # protección 2: jamás lanzarse a sí mismo (evita bucles de procesos)
        print("[alto] el modo profundo ya está corriendo; no se vuelve a lanzar.", file=sys.stderr)
        return 3
    py, prog = PROF / "venv" / "bin" / "python", Path(__file__).resolve().with_name("buscar_profundo.py")
    if not py.exists() or not (PROF / "manifiesto.json").exists():
        print("[aviso] para instalar el modo profundo: python3.12 -I scripts/buscador/preparar_profundo.py (README.md).", file=sys.stderr)
        return 2
    args = [x for x in sys.argv[1:] if x not in ("--profundo", "--ligero", "--maximo")] + ([] if modo == "--profundo" else [modo])  # --ligero (V2 + gte), --profundo (+ vectores e5), --maximo (+ Qwen3 en los 5 mejores)
    aislar = _aislante()
    if aislar is None and not os.environ.get("BUSCADOR_PERMITIR_SIN_SANDBOX"):  # falla cerrado: por seguridad los modelos NO corren sin aislamiento de red del sistema
        print("[ALTO] no hay forma de aislar la red a nivel de sistema (sandbox-exec en macOS; unshare o bwrap en Linux): por seguridad no se corren los modelos. "
              "Con BUSCADOR_PERMITIR_SIN_SANDBOX=1 correrían solo con las capas de archivos y de código (menos seguro).", file=sys.stderr)
        return 4
    if aislar is None:
        print("[aviso] sin aislamiento de red del sistema (BUSCADOR_PERMITIR_SIN_SANDBOX=1): solo las capas de archivos y de código.", file=sys.stderr)
    cmd = (aislar or []) + [str(py), "-I", str(prog)] + args
    return subprocess.run(cmd, env=dict(os.environ, BUSCADOR_SESIONES_EN_PROFUNDO="1")).returncode


def main():
    global INCLUIR_HERR, METODO
    ap = argparse.ArgumentParser(description="Busca en conversaciones pasadas (modo aparte, 100 % local).")
    ap.add_argument("pregunta", nargs="?")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--sesiones", default=str(SES_DEF), help="carpeta o glob de .jsonl (por defecto, solo las de este proyecto)")
    ap.add_argument("--db", default=os.environ.get("BUSCADOR_SESIONES_DB", str(DB_DEF)))
    ap.add_argument("--excluir", nargs="*", default=[], help="prefijos de uuid de sesiones a no indexar (p. ej. la sesión actual)")
    ap.add_argument("--hoy", help="fecha de referencia AAAA-MM-DD para «ayer», «hace N días»…")
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--sin-sync", action="store_true")
    ap.add_argument("--sin-fecha", action="store_true", help="no interpretar fechas en la pregunta")
    ap.add_argument("--herramientas", choices=["si", "no"], help="incluir SQL, comandos y resultados de herramientas en el índice (al cambiar, se reconstruye)")
    ap.add_argument("--ocultar", action="store_true", help="enmascara contraseñas y claves AL MOSTRAR (el índice las conserva)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--util", type=int, metavar="N", help="marca el resultado N de la última consulta como útil (registro local de uso)")
    ap.add_argument("--inutil", type=int, metavar="N", help="marca el resultado N de la última consulta como no útil")
    ap.add_argument("--consulta", help="id de la consulta a marcar (por defecto, la última)")
    ap.add_argument("--sin-registro", action="store_true", help="no guarda esta consulta en el registro de uso (también: BUSCADOR_SESIONES_SIN_REGISTRO=1)")
    ap.add_argument("--uso-stats", action="store_true", help="resume el registro de uso")
    ap.add_argument("--borrar-uso", action="store_true", help="borra todo el registro de uso")
    ap.add_argument("--maximo", action="store_true", help="(valor por defecto si está instalado) cascada: V2 + e5 → gte y Qwen3 sobre los 5 mejores; MRR 0.66; ≈ 7 a 12 s por comando")
    ap.add_argument("--profundo", action="store_true", help="V2 + vectores e5-small → reordenador gte (MRR 0.63; ≈ 5 a 9 s por comando); es el modo por defecto si el Máximo no está instalado")
    ap.add_argument("--ligero", action="store_true", help="V2 + reordenador gte sin vectores (MRR 0.60; ≈ 3 a 7 s por comando); para lo urgente")
    ap.add_argument("--solo-v2", "--ultraligero", dest="solo_v2", action="store_true", help="ULTRA LIGERO: BM25 + prefijos sin modelos (MRR 0.47; la más rápida y la de menor precisión); no es respaldo automático: solo si se pide con la bandera o se elige como modo base")
    ap.add_argument("--modo", nargs="?", const="?", choices=list(MODOS) + ["v2", "?"], help="elige el modo BASE (lo usa toda búsqueda sin bandera; también lo cambia el icono de la barra de menú): ultraligero, ligero, profundo o maximo; sin valor, muestra el actual")
    a = ap.parse_args()
    if a.modo is not None:
        if a.modo != "?": guardar_modo("ultraligero" if a.modo == "v2" else a.modo)
        print("Modo base:", modo_base()); return
    if not (a.ligero or a.profundo or a.maximo or a.solo_v2) and modo_base() == "ultraligero": a.solo_v2 = True
    if a.solo_v2:
        METODO = "buscar_sesiones v" + VERSION + " --solo-v2 (emergencia)"
        print("[ALERTA] Ultra ligero (V2 solo, sin modelos): resultados de menor precisión.", file=sys.stderr)
    elif a.pregunta and not (a.util or a.inutil or a.uso_stats or a.borrar_uso or a.stats or os.environ.get("BUSCADOR_SESIONES_NO_LANZAR")):
        base = modo_base(); qwen_ok = (PROF / "modelos" / "Qwen__Qwen3-Reranker-0.6B" / "config.json").exists()
        modo = "--ligero" if a.ligero else ("--profundo" if a.profundo else ("--maximo" if a.maximo else ("--ligero" if base == "ligero" else ("--profundo" if (base == "profundo" or not qwen_ok) else "--maximo"))))  # sin bandera: el modo base (por defecto Máximo si está instalado)
        rc = lanzar_profundo(modo)
        if rc == 0:
            sys.exit(0)
        if rc != 2:  # el modo profundo está instalado pero falló: NO se cae a V2 solo
            print("[ERROR] la búsqueda profunda falló; no devuelvo resultados de V2 solo (menor precisión). Revisa el aviso de arriba; en una emergencia: --solo-v2.", file=sys.stderr)
            sys.exit(rc)
        print("[ALERTA] el modo con modelos no está instalado en este equipo: esta búsqueda usa V2 SOLO (menor precisión: MRR 0.467 contra 0.631).", file=sys.stderr)
    if a.herramientas:
        INCLUIR_HERR = a.herramientas == "si"
    if a.borrar_uso:
        print(borrar_uso()); return
    if a.uso_stats:
        print(uso_stats()); return
    if a.util or a.inutil:
        print(registrar_marca(a.util or a.inutil, bool(a.util), a.consulta)); return
    con = abrir(a.db); t0 = time.time()
    if not a.sin_sync:
        n = sincronizar(con, a.sesiones, a.excluir, a.reindex)
        print(f"[índice] {n} sesiones actualizadas en {time.time()-t0:.1f}s", file=sys.stderr)
    tot = con.execute("SELECT COUNT(*), COUNT(DISTINCT uuid), MIN(dia), MAX(dia) FROM turnos").fetchone()
    if a.stats or not a.pregunta:
        print(f"{tot[0]} turnos de {tot[1]} sesiones ({tot[2]} a {tot[3]}) · {a.db}")
        return
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else None
    r = buscar(con, a.pregunta, a.k, hoy, not a.sin_fecha, ocultar=a.ocultar)
    cid = None if (a.sin_registro or os.environ.get("BUSCADOR_SESIONES_SIN_REGISTRO")) else registrar_consulta(a.pregunta, r, a.k)
    r["consulta_id"] = cid
    if a.json:
        print(json.dumps(r, ensure_ascii=False, default=str)); return
    if r["filtro_fecha"]:
        print(f"(filtro de fecha: {r['filtro_fecha'][0]} a {r['filtro_fecha'][1]})")
    if not r["resultados"]:
        print("Sin resultados."); return
    for n, x in enumerate(r["resultados"], 1):
        otras = f" · el mismo turno también en {', '.join(dict.fromkeys(x['tambien_en']))}" if x["tambien_en"] else ""
        print(f"{n}. [{x['sesion']}:L{x['linea']}] {x['fecha']} · {x['titulo'][:70]} · confianza {x['confianza']} ({x['cobertura']} términos){otras}\n   {x['fragmento']}")
    print("→ Es un mapa: abre la sesión (uuid:línea) para confirmar y verifica el estado vivo; puede haber decisiones ya superadas (mira la fecha).")
    if cid:
        print(f"→ Consulta {cid} registrada en local. Si usas un fragmento: --util N (o --inutil N).")


if __name__ == "__main__":
    main()
