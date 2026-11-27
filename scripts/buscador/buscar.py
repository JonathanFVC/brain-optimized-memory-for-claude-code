"""V1: buscador indexado de una carpeta de proyecto (documentos, notas, scripts, trazabilidad). Solo librería estándar de Python (sqlite3 + FTS5 + zipfile), sin red, sin servidor.

Uso:  python3 -I scripts/buscador/buscar.py "<pregunta>" [-k 5] [--rutas] [--raiz DIR] [--db ARCHIVO.db] [--reindex]
      --sin-resumen (lista docs/*.md de más de 8 KB sin la línea «> **Resumen:**»)
- Cada consulta sincroniza antes el índice (archivos nuevos, modificados y borrados). No hace falta ningún paso manual.
- Devuelve ruta:línea, encabezado y fragmento (o solo rutas con --rutas); después se lee SOLO ese rango.
- Capa curada OPCIONAL: si existe .context/indice.md o .context/rutas.md (líneas con rutas entre comillas invertidas) y los docs/*.md traen «> **Resumen:** …» bajo el título, esos textos suben el puntaje. Sin ellos funciona igual.
- El índice guarda TODO sin enmascarar (contraseñas incluidas, si estuvieran en la carpeta): es tan sensible como la carpeta. Vive fuera del proyecto (~/.memoria-local, BUSCADOR_HOME), no se copia ni se sube a ningún lado. --ocultar enmascara secretos solo al mostrar.
"""
import argparse
import hashlib
import os
import re
import sqlite3
import sys
import unicodedata
import zipfile
from pathlib import Path

VERSION = "3"
OMITIR_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}  # no se indexan
TEXTO = {".md", ".py", ".sql", ".json", ".jsonl", ".csv", ".tsv", ".txt", ".sh", ".yml", ".yaml", ".html", ".js", ".patch",
         ".toml", ".ini", ".cfg", ""}
DATOS = {".json": 20_000, ".jsonl": 6_000, ".csv": 6_000, ".tsv": 6_000}  # solo cabecera (caracteres)
OFFICE = {".docx", ".xlsx", ".pptx"}
BAJA_PRIORIDAD = (".context/changelog.md", ".context/memoria/", "respaldos/", "CLAUDE.md", ".context/directivas.md",
                  ".context/conexiones.md", ".context/glosario.md")
# copias antiguas de directivas/memoria y el mapa generado: duplican reglas y pueden devolver versiones ya superadas (auditoría 2026-11-20)
EXCLUIR_RUTAS = [re.compile(x) for x in (r"^\.context/directivas-mapa\.md$", r"^scripts/buscador/evaluacion/", r"^\.context/directivas-historial\.md$")]  # la evaluación contiene el texto de las consultas y se contaminaría sola
_SIG = [x for x in os.environ.get("BUSCADOR_SIGLAS", "").lower().replace(" ", "").split(",") if x]
SIGLAS = r"\b(?:" + "|".join(map(re.escape, _SIG)) + r")\b" if _SIG else r"(?!x)x"  # siglas de 2 letras que cuentan como palabra (BUSCADOR_SIGLAS="ab,cd"; por defecto ninguna)
PESO_ENC = 6.0
LEER_MAX = 1_500_000
MAX_TROZOS = 400
VENTANA = 40
MAX_CHARS_MD = 1800
STOP = set("""a al algo ante con contra cual cuando de del desde donde el ella ellos en entre es esa ese eso esta este esto
la las le les lo los me mi mis muy no nos o para pero por que se si sin sobre su sus te tu un una uno unos unas y ya
como cuales cuantos hay hace hacer hacemos ver tiene tienen qué cómo cuál documentos documento archivo archivos script scripts""".split())
SECRETOS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)"), "***CLAVE PRIVADA***"),
    (re.compile(r"(://[^/\s:@]+:)[^@\s/]{3,}(@)"), r"\1***\2"),
    (re.compile(r"(xox[bp]-|lin_api_|ghp_|sk-)[A-Za-z0-9_-]{16,}"), r"\1***"),
    (re.compile(r"(?i)\b(password|passwd|pwd|contrase[nñ]a|secret|api[_-]?key)(\"?\s*[:=]\s*\"?|\s+es\s+)[^\s\"',;|`)<]{4,}"), r"\1\2***"),
]


def enmascarar(t):
    for r, s in SECRETOS:
        t = r.sub(s, t)
    return t


def quitar_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def archivos(raiz):
    for dp, dns, fns in os.walk(raiz):
        dns[:] = [d for d in dns if d not in OMITIR_DIRS]
        for f in fns:
            if f == ".DS_Store":
                continue
            p = Path(dp) / f
            rel = p.relative_to(raiz).as_posix()
            if any(x.search(rel) for x in EXCLUIR_RUTAS):
                continue
            yield rel, p


def _xml_texto(b):
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"</(w:p|a:p|row)>", "\n", b)))


def leer_office(p):
    """Devuelve (texto, encabezado_ficha) de docx/xlsx/pptx usando solo zipfile."""
    try:
        with zipfile.ZipFile(p) as z:
            nombres = z.namelist()
            leer = lambda n, m=2_000_000: z.open(n).read(m).decode("utf-8", "ignore")
            if p.suffix == ".docx":
                return _xml_texto(leer("word/document.xml", 3_000_000)), "[docx]"
            if p.suffix == ".pptx":
                sl = sorted(n for n in nombres if re.match(r"ppt/slides/slide\d+\.xml", n))
                return "\n".join(_xml_texto(leer(n)) for n in sl[:60]), f"[pptx {len(sl)} diapositivas]"
            hojas = re.findall(r'<sheet [^>]*name="([^"]+)"', leer("xl/workbook.xml")) if "xl/workbook.xml" in nombres else []
            cadenas = re.findall(r"<t[^>]*>([^<]*)</t>", leer("xl/sharedStrings.xml", 1_500_000)) if "xl/sharedStrings.xml" in nombres else []
            return "Hojas: " + ", ".join(hojas) + "\n" + "\n".join(cadenas[:600]), f"[xlsx {len(hojas)} hojas: {', '.join(hojas)[:70]}]"
    except Exception as e:  # archivo dañado o con formato raro: queda como ficha
        return "", f"[{p.suffix[1:]} ilegible: {type(e).__name__}]"


def trozos_md(rel, texto):
    lineas = texto.splitlines()
    ruta, buf, enfence, out = [rel.rsplit("/", 1)[-1]], [], False, []

    def cerrar():
        grupo, chars = [], 0
        for n, l in buf + [(None, None)]:
            if n is None or (chars + len(l) > MAX_CHARS_MD and grupo):
                t = "\n".join(x for _, x in grupo).strip()
                if t:
                    out.append((grupo[0][0], grupo[-1][0], " › ".join(ruta[-3:]), t))
                grupo, chars = [], 0
            if n is not None:
                grupo.append((n, l))
                chars += len(l) + 1

    for n, l in enumerate(lineas, 1):
        if l.strip().startswith("```"):
            enfence = not enfence
        m = None if enfence else re.match(r"^(#{1,4})\s+(.*)", l)
        if m:
            cerrar()
            ruta = ruta[: len(m.group(1))] + [re.sub(r"\s*_\(.*?\)_", "", m.group(2)).strip()]
            buf = [(n, l)]
        else:
            buf.append((n, l))
    cerrar()
    return out


def trozos(rel, texto, ficha=""):
    """(línea_inicio, línea_fin, encabezado, texto). Siempre devuelve al menos una ficha para que toda ruta sea encontrable."""
    nombre = rel.rsplit("/", 1)[-1]
    if rel.endswith(".md"):
        out = trozos_md(rel, texto)
    else:
        lineas = texto.splitlines() or [""]
        out = []
        for i in range(0, len(lineas), VENTANA - 5):
            bloque = lineas[i:i + VENTANA]
            enc = next((l.strip()[:80] for l in bloque if re.match(r"\s*(def |class |--|#|/\*|CREATE|SELECT|INSERT|WITH)", l)), "")
            out.append((i + 1, i + len(bloque), f"{nombre} › {enc or ficha or 'contenido'}", "\n".join(bloque)))
    if not out:
        out = [(1, 1, f"{nombre} {ficha}".strip(), "")]
    return out[:MAX_TROZOS]


def contenido(rel, p, tam):
    """(texto, ficha) según el tipo de archivo."""
    ext = p.suffix.lower()
    if ext in OFFICE:
        return leer_office(p)
    if ext in TEXTO:
        cap = DATOS.get(ext, LEER_MAX)
        with open(p, "rb") as f:
            raw = f.read(min(cap, LEER_MAX))
        if b"\x00" in raw[:2000]:
            return "", "[binario]"
        ficha = f"[{ext[1:] or 'texto'} {tam // 1024} KB" + (", solo cabecera]" if ext in DATOS and tam > cap else "]")
        return raw.decode("utf-8", "ignore"), ficha
    return "", f"[{ext[1:] or 'archivo'} {tam // 1024} KB, solo ruta]"


def abrir(db):
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(Path(db).parent, 0o700)
    except OSError:
        pass
    con = sqlite3.connect(db)
    try:
        os.chmod(db, 0o600)
    except OSError:
        pass
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    v = con.execute("SELECT v FROM meta WHERE k='version'").fetchone()
    if not v or v[0] != VERSION:  # esquema distinto: se reconstruye
        con.executescript("DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS chunks;")
        con.execute("INSERT OR REPLACE INTO meta VALUES('version',?)", (VERSION,))
    con.executescript("""
    CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INT, mtime_ns INT, sha1 TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path, l1 UNINDEXED, l2 UNINDEXED, heading, body,
        tokenize='unicode61 remove_diacritics 2');
    """)
    return con


def sincronizar(con, raiz, forzar=False):
    vistos, nuevos, cambiados = set(), 0, 0
    previos = {r[0]: r[1:] for r in con.execute("SELECT path,size,mtime_ns,sha1 FROM files")}
    for rel, p in archivos(raiz):
        vistos.add(rel)
        try:
            st = p.stat()
        except OSError:
            continue
        prev = previos.get(rel)
        if prev and not forzar and prev[0] == st.st_size and prev[1] == st.st_mtime_ns:
            continue
        # hash del archivo completo solo si es pequeño; en los grandes basta tamaño + fecha + cabecera
        if st.st_size <= 20_000_000:
            h = hashlib.sha1()
            with open(p, "rb") as f:
                for blk in iter(lambda: f.read(1 << 20), b""):
                    h.update(blk)
            sha = h.hexdigest()
        else:
            sha = f"big-{st.st_size}-{st.st_mtime_ns}"
        if prev and not forzar and prev[2] == sha:
            con.execute("UPDATE files SET mtime_ns=? WHERE path=?", (st.st_mtime_ns, rel))
            continue
        con.execute("DELETE FROM chunks WHERE path=?", (rel,))
        texto, ficha = contenido(rel, p, st.st_size)
        for l1, l2, enc, txt in trozos(rel, texto, ficha):
            con.execute("INSERT INTO chunks(path,l1,l2,heading,body) VALUES(?,?,?,?,?)",
                        (rel, l1, l2, enc, txt))
        con.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?)", (rel, st.st_size, st.st_mtime_ns, sha))
        nuevos, cambiados = (nuevos + 1, cambiados) if not prev else (nuevos, cambiados + 1)
    borrados = [p for p in previos if p not in vistos]
    for p in borrados:
        con.execute("DELETE FROM chunks WHERE path=?", (p,))
        con.execute("DELETE FROM files WHERE path=?", (p,))
    con.execute("INSERT OR REPLACE INTO meta VALUES('ultima_sync', datetime('now','localtime'))")
    con.commit()
    return nuevos, cambiados, len(borrados)


def consulta_fts(pregunta):
    """OR de términos útiles; IDs con guion (ABC-123) se buscan como frase exacta."""
    q = quitar_acentos(pregunta.lower())
    frases = re.findall(r"[a-z]{2,5}-\d{2,5}", q)
    for f in frases:
        q = q.replace(f, " ")
    palabras = [w for w in re.findall(r"[a-z0-9]{3,}", q) if w not in STOP]
    return " OR ".join([f'"{f}"' for f in frases] + [f'"{w}"' for w in dict.fromkeys(palabras)])


def cargar_alias(raiz):
    out = {}
    try:
        for l in open(raiz / ".context" / "buscador-alias.tsv", encoding="utf-8"):
            if "\t" in l and not l.startswith("#"):
                k, v = l.rstrip("\n").split("\t", 1)
                out[quitar_acentos(k.strip().lower())] = quitar_acentos(v.lower())
    except OSError:
        pass
    return out


def terminos_nuevos(pregunta, raiz=None):
    """(frases-ID, compuestos con _ o ., palabras, extras por alias)."""
    q = quitar_acentos(pregunta.lower())
    frases = re.findall(r"[a-z]{2,5}-\d{2,5}", q)
    for f in frases:
        q = q.replace(f, " ")
    comps = re.findall(r"[a-z0-9]+(?:[_.][a-z0-9]+)+", q)
    pal = [w for w in re.findall(r"[a-z0-9]{3,}", q) if w not in STOP] + re.findall(SIGLAS, q)
    pal = list(dict.fromkeys(pal))
    ext = []
    if raiz:
        al = cargar_alias(raiz)
        for w in set(re.findall(r"[a-z0-9]{2,}", q)):
            if w in al:
                ext += [x for x in re.findall(r"[a-z0-9]{3,}", al[w]) if x not in STOP and x not in pal]
    return frases, comps, pal, list(dict.fromkeys(ext))


def fts_nuevo(fr, co, pal, ext, op):
    t = [f'"{f}"' for f in fr]
    t += ['"' + re.sub(r"[_.]", " ", c) + '"' for c in co]
    t += [f'"{w}"' for w in pal]
    if op == "OR":
        t += [f'"{w}"' for w in ext]
    return f" {op} ".join(t)


def prior(p):
    """Multiplicador del puntaje (>1 sube, <1 baja) según de dónde viene el trozo."""
    if p.startswith("respaldos/"):
        return 0.4
    if re.search(r"\.(json|jsonl|csv|tsv|ok)$", p):
        return 0.5
    if p.startswith((".context/changelog", ".context/memoria/")):
        return 0.5
    if p.startswith("docs/"):
        return 1.5
    if p.startswith(".context/"):
        return 1.3
    if p.startswith(("scripts/", "entregables/")):
        return 0.8
    return 1.0


def curado(raiz):
    """Nivel 1: líneas de rutas.md/indice.md y resúmenes de docs/ (escritas a mano) -> {ruta: rutas citadas}. En memoria."""
    filas = []
    for rel in (".context/rutas.md", ".context/indice.md"):
        try:
            for l in open(raiz / rel, encoding="utf-8"):
                ps = [x.rstrip("/.,;:)") for x in re.findall(r"`((?:docs|scripts|entregables|proyectos|\.context)/[^`\s]+)`", l)]
                if ps:
                    filas.append((l, ps))
        except OSError:
            pass
    for f in sorted((raiz / "docs").glob("*.md")):
        try:
            for l in open(f, encoding="utf-8").read().splitlines()[:8]:
                if l.startswith("> **Resumen:**"):
                    filas.append((f.stem.replace("-", " ") + " " + l, [f"docs/{f.name}"]))
        except OSError:
            pass
    m = sqlite3.connect(":memory:")
    m.execute("CREATE VIRTUAL TABLE c USING fts5(texto, tokenize='unicode61 remove_diacritics 2')")
    for i, (t, _) in enumerate(filas):
        m.execute("INSERT INTO c(rowid,texto) VALUES(?,?)", (i + 1, t))
    return m, filas


def rankear(con, raiz, pregunta, clasico=False, peso_enc=None):
    """[(ruta, l1, l2, encabezado, cuerpo, puntaje)] del mejor al peor. clasico=True: ranking anterior (OR + penalizaciones)."""
    pe = PESO_ENC if peso_enc is None else peso_enc
    if clasico:
        fts = consulta_fts(pregunta)
        if not fts:
            return []
        filas = con.execute("SELECT path,l1,l2,heading,body,bm25(chunks,3.0,0,0,6.0,1.0) FROM chunks WHERE chunks MATCH ? ORDER BY 6 LIMIT 150", (fts,)).fetchall()
        pide = bool(re.search(r"contrase|password|credencial|clave|secret|token", quitar_acentos(pregunta.lower())))

        def peso(r):
            return 0.45 if (r[0].startswith(BAJA_PRIORIDAD) or "/respaldos/" in r[0]) else 1.0
        filas.sort(key=lambda r: r[5] * peso(r))
        return [(r[0], r[1], r[2], r[3], r[4], r[5] * peso(r)) for r in filas]
    fr, co, pal, ext = terminos_nuevos(pregunta, raiz)
    f_or = fts_nuevo(fr, co, pal, ext, "OR")
    if not f_or:
        return []
    sql = "SELECT rowid,path,l1,l2,heading,body,bm25(chunks,3.0,0,0,?,1.0) FROM chunks WHERE chunks MATCH ? ORDER BY 7 LIMIT 300"
    try:
        filas = con.execute(sql, (pe, f_or)).fetchall()
        and_ids = {r[0] for r in con.execute(sql, (pe, fts_nuevo(fr, co, pal, ext, "AND"))).fetchall()}
    except sqlite3.OperationalError:
        return []
    pide = bool(re.search(r"contrase|password|credencial|clave|secret|token|usuari|permis|grant|\brol\b|cuenta|host|conexion|acceso",
                          quitar_acentos(pregunta.lower())))
    cred, idt = {}, [t.replace("_", "-") for t in fr] + [re.sub(r"[_.]", "-", c) for c in co]
    try:
        m, cf = curado(raiz)
        for (rid,), mult in zip(m.execute("SELECT rowid FROM c WHERE c MATCH ? ORDER BY bm25(c) LIMIT 3", (f_or,)).fetchall(), (2.2, 1.7, 1.4)):
            for x in cf[rid - 1][1]:
                cred[x] = max(cred.get(x, 1.0), mult)
    except sqlite3.OperationalError:
        pass
    out = []
    for rid, p, l1, l2, enc, body, s in filas:
        mlt = prior(p)
        if rid in and_ids:
            mlt *= 1.6
        for t in idt:
            if t and t in p.lower():
                mlt *= 2.5
            elif t and t in enc.lower():
                mlt *= 1.5
        for cp, cm in cred.items():
            if p == cp or p.startswith(cp.rstrip("/") + "/"):
                mlt *= cm
                break
        out.append((p, l1, l2, enc, body, s * mlt))
    out.sort(key=lambda r: r[5])
    return out


def fragmento(texto, terminos, ancho=230, ocultar=False):
    plano = quitar_acentos(texto.lower())
    pos = max(min([plano.find(t) for t in terminos if t in plano] or [0]), 0)
    s = re.sub(r"\s+", " ", texto[max(0, pos - 60):max(0, pos - 60) + ancho]).strip()
    return enmascarar(s) if ocultar else s


def resumen(raiz, rel):
    """Línea «> **Resumen:** …» al inicio de un .md (si existe), para decidir sin abrir el documento."""
    if not rel.endswith(".md"):
        return ""
    try:
        with open(raiz / rel, encoding="utf-8") as f:
            for _, l in zip(range(12), f):
                if l.startswith("> **Resumen:**"):
                    return l[14:].strip()[:170]
    except OSError:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pregunta", nargs="?")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--rutas", action="store_true", help="solo rutas y encabezados, sin fragmentos")
    ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--db", default=os.environ.get("BUSCADOR_DB", str(Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "index.db")))
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--sin-resumen", action="store_true", help="lista docs/*.md de más de 8 KB sin línea de resumen")
    ap.add_argument("--clasico", action="store_true", help="usa el ranking anterior (OR + penalizaciones) para comparar")
    ap.add_argument("--compactar", action="store_true", help="VACUUM del índice tras sincronizar")
    ap.add_argument("--ocultar", action="store_true", help="enmascara contraseñas y claves al mostrar (el índice las conserva)")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    con = abrir(a.db)
    n, c, b = sincronizar(con, raiz, a.reindex)
    total = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    print(f"[índice] {total} archivos (+{n} nuevos, ~{c} cambiados, -{b} borrados)", file=sys.stderr)
    if a.sin_resumen:
        for p in sorted((raiz / "docs").glob("*.md")):
            if p.stat().st_size > 8192 and not resumen(raiz, f"docs/{p.name}"):
                print(f"{p.stat().st_size // 1024} KB docs/{p.name}")
        return
    if a.compactar:
        con.commit()
        con.execute("VACUUM")
    if not a.pregunta:
        return
    fr, co, pal, ext = terminos_nuevos(a.pregunta, raiz)
    if not (fr or co or pal) and not a.clasico:
        print("Sin términos útiles en la pregunta.")
        return
    filas = rankear(con, raiz, a.pregunta, clasico=a.clasico)
    terminos = fr + [re.sub(r"[_.]", " ", c) for c in co] + pal + ext
    vistos, n_out = {}, 0
    tope = 1 if a.rutas else 2
    for path, l1, l2, enc, body, r in filas:
        if vistos.get(path, 0) >= tope or n_out >= a.k:
            continue
        vistos[path] = vistos.get(path, 0) + 1
        n_out += 1
        res = resumen(raiz, path) if n_out <= 3 else ""
        res = f"\n   ↳ {res}" if res else ""
        if a.rutas:
            print(f"{n_out}. {path}:L{l1}-L{l2} | {enc[:70]}{res}")
        else:
            print(f"{n_out}. {path}:L{l1}-L{l2} | {enc[:90]}{res}\n   {fragmento(body, terminos, ocultar=a.ocultar)}")
    if n_out == 0:
        print("Sin resultados.")


if __name__ == "__main__":
    main()
