"""V1 PROFUNDA (2026-11-26): búsqueda de la CARPETA (buscar.py: documentos, trazabilidad, directivas, memorias) con modelos. Receta medida (51 consultas: primer lugar 82 % → 96 %, MRR 0.898 → 0.973):
RRF(producción, e5, gte): el ranking de buscar.py (capa curada + prioridades) se mezcla con el orden por significado de e5 y con el de gte sobre los 50 mejores de la mezcla producción + e5. Modo «ligero» = RRF(producción, gte) con 50 candidatos; «rapido» = solo buscar.py.
Los vectores de los trozos se guardan en una base aparte y se actualizan solos (solo lo nuevo o cambiado). Sin red: lo corre buscar_todo_modelos.py dentro del entorno aislado."""
import collections, hashlib, os, sqlite3, sys
import numpy as np

KEY = lambda r: (r[0], r[1], r[2])
doc = lambda r: f"{r[0]} — {r[3]}. {r[4][:1100]}"


def fuse(listas, pesos, k=60):
    sc, obj = collections.defaultdict(float), {}
    for L, w in zip(listas, pesos):
        for i, r in enumerate(L): sc[KEY(r)] += w / (k + i); obj[KEY(r)] = r
    return [obj[x] for x in sorted(sc, key=lambda x: -sc[x])]


class Carpeta:
    def __init__(self, B, con, raiz, vec_db, e5, ce):
        self.B, self.con, self.raiz, self.vec_db, self.e5, self.ce, self.E = B, con, raiz, vec_db, e5, ce, None
        self.CH = [(p, l1, l2, enc, body, 0.0) for p, l1, l2, enc, body in con.execute("SELECT path,l1,l2,heading,body FROM chunks")]

    def preparar(self):
        """Deja al día los vectores de todos los trozos (solo se vectoriza lo nuevo o cambiado)."""
        if self.e5 is None: return
        self.vec_db.parent.mkdir(parents=True, exist_ok=True)
        vdb = sqlite3.connect(str(self.vec_db), timeout=60); vdb.execute("CREATE TABLE IF NOT EXISTS vec(k TEXT PRIMARY KEY, h TEXT, v BLOB)")
        try: os.chmod(self.vec_db, 0o600)
        except OSError: pass
        tengo = dict(vdb.execute("SELECT k,h FROM vec")); claves = [f"{r[0]}\x00{r[1]}\x00{r[2]}" for r in self.CH]
        hs = [hashlib.sha1(doc(r).encode("utf-8")).hexdigest()[:16] for r in self.CH]
        falta = [i for i, (k, h) in enumerate(zip(claves, hs)) if tengo.get(k) != h]
        if falta:
            print(f"[carpeta] vectorizando {len(falta)} trozos nuevos o cambiados (e5-small)…", file=sys.stderr, flush=True)
            for j in range(0, len(falta), 256):
                ch = falta[j:j + 256]
                V = self.e5.encode(["passage: " + doc(self.CH[i]) for i in ch], batch_size=64, normalize_embeddings=True, show_progress_bar=False).astype("float32")
                vdb.executemany("INSERT OR REPLACE INTO vec VALUES(?,?,?)", [(claves[i], hs[i], V[n].tobytes()) for n, i in enumerate(ch)]); vdb.commit()
        vivos = set(claves); obsoletos = [(k,) for k in tengo if k not in vivos]
        if obsoletos: vdb.executemany("DELETE FROM vec WHERE k=?", obsoletos); vdb.commit()
        mapa = dict(vdb.execute("SELECT k,v FROM vec")); vdb.close()
        self.E = np.stack([np.frombuffer(mapa[k], dtype="float32") for k in claves]) if claves else np.zeros((0, 384), "float32")

    def _gte(self, q, cand):
        g = np.array([float(s) for s in self.ce.predict([(q, doc(r)) for r in cand], batch_size=16, show_progress_bar=False)])
        return [cand[j] for j in np.argsort(-g, kind="stable")]

    def buscar(self, q, modo="profundo"):
        base = self.B.rankear(self.con, self.raiz, q)
        if modo == "rapido" or len(base) < 2 or self.ce is None: return base
        if modo == "ligero" or self.E is None or self.e5 is None:
            return fuse([base[:50], self._gte(q, base[:50])], [1, 1]) + base[50:]
        qv = self.e5.encode(["query: " + q], normalize_embeddings=True, show_progress_bar=False)[0]
        raw = [self.CH[i] for i in np.argsort(-(self.E @ qv))[:100]]; P = base[:100]
        return fuse([P, raw, self._gte(q, fuse([P, raw], [1, 1])[:50])], [1, 1, 1]) + base
