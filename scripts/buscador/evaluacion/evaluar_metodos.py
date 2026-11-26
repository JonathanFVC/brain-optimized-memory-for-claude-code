"""Compara métodos de búsqueda sobre TUS preguntas de control: V2 solo · e5 solo · e5 → gte (K = 20, 50, 100) · ligero (V2 → gte) · profundo (V2 + e5 → gte). Mide top 5 / MRR con anclas por regex.
Trabaja SOLO SOBRE COPIAS del índice y de los vectores (abrir el índice real en otro modo lo vacía). Uso (con el Python del entorno aislado, sin red):
  ~/.memoria-local/profundo/venv/bin/python -I scripts/buscador/evaluacion/probar_modelos_sin_v2.py PREGUNTAS.tsv
PREGUNTAS.tsv: id<TAB>tipo<TAB>pregunta<TAB>ancla1<TAB>ancla2 (ancla = regex que debe aparecer en el turno correcto; tipo M exige las dos anclas; sin cabecera; # comenta). Ver evaluacion/preguntas.ejemplo.tsv."""
import collections, importlib.util, os, random, re, shutil, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
# TRABAJA SOLO SOBRE COPIAS: abrir el índice real en otro modo lo vacía y preparar() borra los vectores que no ve
H = Path(os.environ.get("BUSCADOR_HOME") or Path.home() / ".memoria-local"); import tempfile; TMP = Path(tempfile.mkdtemp(prefix="memoria-local-eval-")); TMP.mkdir(parents=True, exist_ok=True)
shutil.copy(H / "sesiones.db", TMP / "sesiones.db"); shutil.copy(H / "profundo" / "vectores.db", TMP / "vectores.db"); os.environ["BUSCADOR_PROFUNDO_VEC"] = str(TMP / "vectores.db")
sp = importlib.util.spec_from_file_location("bp", AQUI / "buscar_profundo.py"); bp = importlib.util.module_from_spec(sp); sp.loader.exec_module(bp)
bs = bp.bs; EXCL = tuple(sys.argv[2:])  # prefijos de uuid de sesiones a excluir (p. ej. la sesión en curso)
log = lambda *x: print(time.strftime("%H:%M:%S"), *x, flush=True)

con = bs.abrir(TMP / "sesiones.db"); bp.verificar_modelos(); bp.LIGERO = False
S = bp.preparar(con); np, ce, e5, Ed, ids = S["np"], S["ce"], S["e5"], S["Ed"], S["ids"]
filas = con.execute("SELECT id, uuid, titulo, usuario, asistente FROM turnos ORDER BY id").fetchall()
TX = {f[0]: "\n".join(x or "" for x in f[2:5]) for f in filas}; US = {f[0]: (f[1], bs.norm(f[3] or "")[:200]) for f in filas}; DOC = {f[0]: bp._doc(f[2], f[3], f[4]) for f in filas}
fuera = {f[0] for f in filas if f[1].startswith(EXCL)}; pos_id = {i: k for k, i in enumerate(ids)}
log(f"turnos {len(filas)} (se excluyen {len(fuera)} de las sesiones en curso); dispositivo {S['dispositivo']}")


def leer(f):
    out = []
    for l in open(f, encoding="utf-8"):
        if not l.strip() or l.startswith("#"): continue
        c = l.rstrip("\n").split("\t") + [""] * 5
        out.append(dict(id=c[0], tipo=c[1] or "T", q=c[2], a1=c[3], a2=c[4]))
    return out


def fin(lista, k=5, cap=2):
    out, vs, vistos = [], collections.defaultdict(int), set()
    for i in lista:
        u, c = US[i]
        if vs[u] >= cap or c in vistos: continue
        vs[u] += 1; vistos.add(c); out.append(i)
        if len(out) >= k: break
    return out


def rango(l, c):
    tx = [TX[i] for i in l]; p1 = next((k + 1 for k, t in enumerate(tx) if re.search(c["a1"], t)), None)
    if c["tipo"] != "M": return p1
    p2 = next((k + 1 for k, t in enumerate(tx) if re.search(c["a2"], t)), None); return max(p1, p2) if p1 and p2 else None


rr = lambda p: 1 / p if p and p <= 5 else 0.
CONJ = {"preguntas": leer(sys.argv[1])}
METODOS = ["V2 solo", "e5 solo", "e5 → gte (K=20)", "e5 → gte (K=50)", "e5 → gte (K=100)", "Ligero: V2 → gte", "Profundo: V2 + e5 → gte"]
cache = {}


def gte(q, cand):
    falta = [i for i in cand if (q, i) not in cache]
    if falta:
        for i, s in zip(falta, ce.predict([(q, DOC[i]) for i in falta], batch_size=16, show_progress_bar=False)): cache[(q, i)] = float(s)
    return sorted(cand, key=lambda i: -cache[(q, i)])


M = collections.defaultdict(lambda: collections.defaultdict(list)); aparte = collections.defaultdict(list); acierto100 = collections.defaultdict(list)
for nom, Q in CONJ.items():
    for c in Q:
        q = c["q"]; t = list(dict.fromkeys(bs.palabras(q)))
        pal = [i for i in bs._lista(con, "t_pal", " OR ".join(f'"{x}"' for x in t), None) if i not in fuera]; prf = [i for i in bs._lista(con, "t_pref", " OR ".join(f'"{x}"' for x in dict.fromkeys(bs.pref(x) for x in t)), None) if i not in fuera]
        v2 = bs._rrf(pal, prf)[:100]
        qv = e5.encode(["query: " + q], normalize_embeddings=True, show_progress_bar=False)[0]; sim = Ed @ qv
        emb = [ids[j] for j in np.argsort(-sim) if ids[j] not in fuera][:100]
        prof = bs._rrf(pal, prf, emb)[:100]
        r = {"V2 solo": v2, "e5 solo": emb, "e5 → gte (K=20)": gte(q, emb[:20]) + emb[20:], "e5 → gte (K=50)": gte(q, emb[:50]) + emb[50:], "e5 → gte (K=100)": gte(q, emb[:100]),
             "Ligero: V2 → gte": gte(q, v2[:20]) + v2[20:], "Profundo: V2 + e5 → gte": gte(q, prof[:20]) + prof[20:]}
        for k in METODOS: M[nom][k].append(rr(rango(fin(r[k]), c)))
        acierto100["e5"].append(any(re.search(c["a1"], TX[i]) for i in emb)); acierto100["V2"].append(any(re.search(c["a1"], TX[i]) for i in v2))
    log(f"{nom}: listo ({len(cache)} pares calificados por gte)")

rnd = random.Random(7)
def boot(x, y, B=2000):
    n = len(x); df = [p - q for p, q in zip(x, y)]; ms = sorted(sum(df[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B)); return sum(df) / n, ms[int(.025 * B)], ms[int(.975 * B) - 1]


todo = {k: sum((M[n][k] for n in CONJ), []) for k in METODOS}
print(f"\nMRR (top 5, tope 2 por sesión) en las {len(todo['V2 solo'])} preguntas\n{'método':<26}" + "".join(f"{n:>14}" for n in CONJ) + f"{'todas':>8}   ΔMRR vs profundo [IC95]       ΔMRR vs ligero [IC95]")
f = lambda x: f"{x[0]:+.3f} [{x[1]:+.3f}, {x[2]:+.3f}]" + (" *" if x[1] > 0 or x[2] < 0 else "")
for k in METODOS:
    a = None if k.startswith("Profundo") else boot(todo[k], todo["Profundo: V2 + e5 → gte"]); b = None if k.startswith("Ligero") else boot(todo[k], todo["Ligero: V2 → gte"])
    print(f"{k:<26}" + "".join(f"{sum(M[n][k]) / len(M[n][k]):>14.3f}" for n in CONJ) + f"{sum(todo[k]) / len(todo[k]):>8.3f}   {f(a) if a else '':<28}{f(b) if b else ''}")
print(f"\nLa respuesta está entre los 100 primeros candidatos (techo de lo que gte puede reordenar): e5 {sum(acierto100['e5'])}/{len(acierto100['e5'])} · V2 {sum(acierto100['V2'])}/{len(acierto100['V2'])}")

shutil.rmtree(TMP, ignore_errors=True)  # las copias tienen texto de tus conversaciones
