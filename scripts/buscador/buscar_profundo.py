"""Búsqueda con modelos de buscar_sesiones.py (modos ligero, profundo y máximo): V2 (BM25 + prefijos) + vectores multilingual-e5-small (RRF) + reordenador gte-multilingual-reranker-base sobre los 20 mejores; en el modo máximo, Qwen3-Reranker-0.6B reordena además los 5 mejores y se promedia con gte (puntaje z).
Se lanza con:  python3 -I scripts/buscador/buscar_sesiones.py "<pregunta>" --profundo   (corre con el Python de ~/.memoria-local/profundo/venv, dentro de sandbox-exec sin red en macOS).
SIN RED, TRES CAPAS: (1) archivos: modelos propios en carpeta de solo lectura, con huellas SHA-256 verificadas contra manifiesto.json; (2) código: modo sin conexión forzado
ANTES de importar las librerías, carga solo desde rutas locales y se bloquean los sockets de red de Python; (3) sistema: sandbox-exec (deny network*) lo pone el lanzador (solo macOS)."""
import logging, os, socket, sys

# ---- capa de código: modo sin conexión ANTES de importar torch, transformers y sentence-transformers
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false", DO_NOT_TRACK="1", HF_HUB_DISABLE_PROGRESS_BARS="1", TRANSFORMERS_VERBOSITY="error")
for _n in ("torch.distributed.elastic.multiprocessing.redirects", "sentence_transformers", "transformers", "huggingface_hub"):  # menos ruido en la salida (cuesta tokens): avisos y barras de carga
    logging.getLogger(_n).setLevel(logging.ERROR)
_connect_orig = socket.socket.connect


def _sin_red(*a, **k):
    raise OSError("sin red: conexión bloqueada por buscar_profundo.py (modo local)")


def _connect(self, address):
    if self.family == getattr(socket, "AF_UNIX", None):  # sockets locales de archivo: no salen del equipo
        return _connect_orig(self, address)
    return _sin_red(address)


socket.socket.connect = _connect
socket.socket.connect_ex = lambda self, address: _sin_red(address)
socket.socket.sendto = lambda self, *a, **k: _sin_red()
socket.create_connection = _sin_red
socket.getaddrinfo = _sin_red

import datetime, hashlib, importlib.util, json, sqlite3, time
from collections import defaultdict
from pathlib import Path

PROF = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local") / "profundo"
MOD = PROF / "modelos"
E5, GTE = MOD / "intfloat__multilingual-e5-small", MOD / "Alibaba-NLP__gte-multilingual-reranker-base"
VEC = Path(os.environ.get("BUSCADOR_PROFUNDO_VEC", str(PROF / "vectores.db")))
K_CAND = 20
LIGERO = False  # --ligero: reordenador gte sobre V2, sin vectores ni e5
QWEN = MOD / "Qwen__Qwen3-Reranker-0.6B"; M_QWEN = 5
MAXIMO = False  # --maximo: además, Qwen3-Reranker reordena los 5 mejores de gte (promedio z con gte); medido: MRR 0.662 contra 0.628 del profundo
sp = importlib.util.spec_from_file_location("bs", Path(__file__).resolve().with_name("buscar_sesiones.py")); bs = importlib.util.module_from_spec(sp); sp.loader.exec_module(bs)
ST = {}  # modelos y vectores, cargados una sola vez


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def verificar_modelos(forzar=False):
    """Capa de archivos: tamaño y fecha de cada archivo contra manifiesto.json; si algo cambió, huella SHA-256 completa; si no coincide, se aborta."""
    mf = json.loads((PROF / "manifiesto.json").read_text(encoding="utf-8"))
    for rel, m in mf["archivos"].items():
        p = PROF / rel
        if not p.exists():
            sys.exit(f"ALTO: falta {rel} (modelo incompleto). Corre preparar_profundo.py.")
        st = p.stat()
        if forzar or st.st_size != m["size"] or st.st_mtime_ns != m["mtime_ns"]:
            if _sha(p) != m["sha256"]:
                sys.exit(f"ALTO: {rel} fue alterado (huella distinta). No se carga el modelo.")
    return len(mf["archivos"])


def _doc(t, u, a):  # mismo texto con el que se midió
    return (t or "").split(" · ")[0] + ". " + (u or "")[:400] + " " + (a or "")[:900]


def _vectores(con, e5, np, filas):
    """Deja al día los vectores de todos los turnos (solo se vectorizan los nuevos o cambiados) y devuelve la matriz alineada con `filas`."""
    VEC.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(VEC.parent, 0o700)
    except OSError:
        pass
    vdb = sqlite3.connect(str(VEC), timeout=60); vdb.execute("CREATE TABLE IF NOT EXISTS vec(uuid TEXT, l1 INT, h TEXT, v BLOB, PRIMARY KEY(uuid, l1))")
    try:
        os.chmod(VEC, 0o600)
    except OSError:
        pass
    tengo = {(u, l): h for u, l, h in vdb.execute("SELECT uuid, l1, h FROM vec")}
    vivos, falta = set(), []
    for _, u, l, t, us, a, _ in filas:
        d = _doc(t, us, a); h = hashlib.sha1(d.encode("utf-8")).hexdigest()[:16]; vivos.add((u, l))
        if tengo.get((u, l)) != h:
            falta.append((u, l, h, d))
    if falta:
        print(f"[profundo] vectorizando {len(falta)} turnos nuevos o cambiados (e5-small)…", file=sys.stderr, flush=True)
        for j in range(0, len(falta), 256):
            ch = falta[j:j + 256]
            V = e5.encode(["passage: " + d for *_, d in ch], batch_size=16, normalize_embeddings=True, show_progress_bar=False).astype("float32")
            vdb.executemany("INSERT OR REPLACE INTO vec VALUES(?,?,?,?)", [(u, l, h, V[i].tobytes()) for i, (u, l, h, _) in enumerate(ch)])
            vdb.commit()
    obsoletos = [k for k in tengo if k not in vivos]
    if obsoletos:
        vdb.executemany("DELETE FROM vec WHERE uuid=? AND l1=?", obsoletos); vdb.commit()
    mapa = {(u, l): v for u, l, v in vdb.execute("SELECT uuid, l1, v FROM vec")}
    return np.stack([np.frombuffer(mapa[(f[1], f[2])], dtype="float32") for f in filas]) if filas else np.zeros((0, 384), "float32")


def preparar(con):
    """Carga el reordenador gte (siempre) y, salvo en modo --ligero, e5 y los vectores. Si los vectores fallan se sigue en modo ligero (gte sobre V2): NUNCA se devuelve V2 solo."""
    if ST.get("con") is con:
        return ST
    import numpy as np, torch
    from sentence_transformers import CrossEncoder, SentenceTransformer
    import transformers; transformers.utils.logging.disable_progress_bar()
    torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    t0 = time.time()
    ce = CrossEncoder(str(GTE), max_length=512, device=dev, trust_remote_code=False, local_files_only=True)
    qw = CrossEncoder(str(QWEN), max_length=512, device=dev, trust_remote_code=False, local_files_only=True) if MAXIMO else None
    filas = con.execute("SELECT id, uuid, l1, titulo, usuario, asistente, dia FROM turnos ORDER BY id").fetchall()
    e5, Ed, completo = None, None, False
    if not LIGERO:
        try:
            e5 = SentenceTransformer(str(E5), device=dev, trust_remote_code=False, local_files_only=True); e5.max_seq_length = 256
            Ed = _vectores(con, e5, np, filas); completo = True
        except Exception as e:
            print(f"[profundo] vectores no disponibles ({type(e).__name__}: {str(e)[:90]}); sigo en modo ligero (gte sobre V2).", file=sys.stderr)
    bs.METODO = "buscar_sesiones v" + bs.VERSION + ((" --maximo (e5-small + gte-reranker, K=20, + Qwen3-Reranker en los 5 mejores)" if qw is not None else " --profundo (e5-small + gte-reranker, K=20)") if completo else " --ligero (gte-reranker sobre V2, K=20)")
    ST.update(con=con, np=np, e5=e5, ce=ce, qw=qw, ids=[f[0] for f in filas], Ed=Ed, completo=completo, dia={f[0]: f[6] for f in filas}, arranque=time.time() - t0, dispositivo=dev)
    return ST


def buscar_p(con, pregunta, k=5, hoy=None, usar_fecha=True, tope_sesion=2, ocultar=False, herr=None):
    """Misma interfaz y salida que buscar_sesiones.buscar, con vectores y reordenador."""
    hoy = hoy or datetime.date.today(); rango, q = None, pregunta
    if usar_fecha:
        f = bs.fechas_es(pregunta, hoy)
        if f:
            rango, q = (f[0], f[1]), f[2]
    terminos = list(dict.fromkeys(bs.palabras(q)))
    if not terminos:
        return {"resultados": [], "filtro_fecha": rango, "terminos": []}
    herr = bool(bs.CUE_HERR.search(bs.norm(pregunta))) if herr is None else herr
    ex_p = " OR ".join(f'"{t}"' for t in terminos); ex_f = " OR ".join(f'"{t}"' for t in dict.fromkeys(bs.pref(t) for t in terminos))
    S = preparar(con); np = S["np"]
    if S["completo"]:
        qv = S["e5"].encode(["query: " + q], normalize_embeddings=True, show_progress_bar=False)[0]
        orden = np.argsort(-(S["Ed"] @ qv))

    def listas(rg):
        L = [bs._lista(con, "t_pal", ex_p, rg), bs._lista(con, "t_pref", ex_f, rg)]
        if herr:
            L += [bs._lista_h(con, "h_pal", ex_p, rg), bs._lista_h(con, "h_pref", ex_f, rg)]
        n_lex = len(L)
        if not S["completo"]:
            return L, n_lex
        cand = (S["ids"][j] for j in orden)
        emb = [i for i in cand if (not rg or rg[0].isoformat() <= S["dia"][i] <= rg[1].isoformat())][:100]
        return L + [emb], n_lex
    L, n_lex = listas(rango)
    if rango and not any(L[:n_lex]):  # sin nada ese día: se repite sin filtro y se avisa
        L, n_lex = listas(None); rango = None
    base = bs._rrf(*L)[:100]; top, resto = base[:K_CAND], base[K_CAND:]
    if top:
        filas = {i: con.execute("SELECT titulo, usuario, asistente FROM turnos WHERE id=?", (i,)).fetchone() for i in top}
        sc = S["ce"].predict([(q, _doc(*filas[i])) for i in top], batch_size=16, show_progress_bar=False)
        par = sorted(zip(sc, top), key=lambda x: -x[0]); top = [i for _, i in par]
        if S.get("qw") is not None and len(top) > 1:  # MÁXIMO: segunda etapa; Qwen3 reordena los mejores M_QWEN de gte y se promedian los puntajes (z dentro de esos M)
            m = min(M_QWEN, len(top)); cabeza = top[:m]; g = [float(s) for s, _ in par[:m]]
            qs = S["qw"].predict([(q, _doc(*filas[i])) for i in cabeza], batch_size=16, show_progress_bar=False)
            z = lambda v: [(x - float(np.mean(v))) / float(np.std(v)) if float(np.std(v)) > 1e-9 else 0. for x in v]
            top = [cabeza[j] for j in np.argsort(-np.mean([z(g), z([float(s) for s in qs])], axis=0), kind="stable")] + top[m:]
    out, vs, vistos = [], defaultdict(int), {}
    for i in top + resto:
        r = con.execute("SELECT uuid,titulo,l1,l2,ts,dia,usuario,asistente,herramientas FROM turnos WHERE id=?", (i,)).fetchone()
        if not r or vs[r[0]] >= tope_sesion:
            continue
        clave = bs.norm(r[6])[:200]
        if clave in vistos:
            vistos[clave]["tambien_en"].append(r[0][:8]); continue
        vs[r[0]] += 1
        texto = "USUARIO: " + r[6] + "\nCLAUDE: " + r[7] + ("\nHERRAMIENTAS: " + r[8] if r[8] else "")
        pres = set(bs.palabras(texto)); cob = sum(1 for t in terminos if t in pres)
        nivel = "alta" if cob >= 0.7 * len(terminos) else ("media" if cob >= 0.4 * len(terminos) else "baja")
        out.append({"id": i, "sesion": r[0][:8], "uuid": r[0], "linea": r[2], "linea_fin": r[3], "fecha": r[5], "titulo": r[1], "confianza": nivel, "cobertura": f"{cob}/{len(terminos)}",
                    "fragmento": (bs.enmascarar if ocultar else (lambda t: t))(bs._fragmento(texto, terminos)), "tambien_en": []})
        vistos[clave] = out[-1]
        if len(out) >= k:
            break
    ST["sugerir"] = bool(LIGERO and out and all(x["confianza"] == "baja" for x in out))  # el ligero no está seguro: se sugiere repetir con --profundo
    return {"resultados": out, "filtro_fecha": rango, "terminos": terminos}


def probar_sin_red():
    """Prueba automática de la capa de código: todo intento de conexión debe fallar."""
    import urllib.request
    fallos = 0
    pruebas = [("socket.create_connection a 1.1.1.1:443", lambda: socket.create_connection(("1.1.1.1", 443), timeout=3)),
               ("resolver huggingface.co", lambda: socket.getaddrinfo("huggingface.co", 443)),
               ("socket TCP .connect()", lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("1.1.1.1", 443))),
               ("UDP sendto", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"x", ("1.1.1.1", 53))),
               ("urllib a https://huggingface.co", lambda: urllib.request.urlopen("https://huggingface.co", timeout=3))]
    for nombre, f in pruebas:
        try:
            f(); print(f"FALLO  {nombre}: la conexión NO se bloqueó"); fallos += 1
        except Exception as e:
            print(f"ok     {nombre}: bloqueada ({type(e).__name__})")
    print(f"HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE')} TRANSFORMERS_OFFLINE={os.environ.get('TRANSFORMERS_OFFLINE')}")
    return fallos


def main():
    if "--probar-sin-red" in sys.argv:
        sys.exit(1 if probar_sin_red() else 0)
    global LIGERO, MAXIMO
    LIGERO = "--ligero" in sys.argv; MAXIMO = "--maximo" in sys.argv and not LIGERO
    sys.argv = [sys.argv[0]] + [x for x in sys.argv[1:] if x not in ("--profundo", "--ligero", "--maximo")]
    if MAXIMO and not (QWEN / "config.json").exists():
        print("[aviso] el nivel Máximo no está instalado (falta Qwen3-Reranker): sigo en profundo. Para instalarlo: python3 -I scripts/buscador/preparar_maximo.py", file=sys.stderr); MAXIMO = False
    n = verificar_modelos(forzar="--verificar-modelos" in sys.argv)
    sys.argv = [x for x in sys.argv if x != "--verificar-modelos"]
    bs.buscar = buscar_p
    os.environ["BUSCADOR_SESIONES_NO_LANZAR"] = "1"  # protección 1: el main() de V2 NO vuelve a lanzar el modo profundo (esta ya es la corrida profunda: bs.buscar está reemplazada)
    bs.main()
    if ST.get("sugerir") and "--json" not in sys.argv:
        print("→ Sugerencia: confianza baja en todos los resultados; repite con una búsqueda profunda (sin --ligero).")


if __name__ == "__main__":
    main()
