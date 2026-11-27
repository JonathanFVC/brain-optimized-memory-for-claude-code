"""CALIBRADOR del enrutador (2026-11-27): el enrutador arranca buscando en las DOS fuentes (V1 + V2) y, con las marcas de uso del propio usuario, va ganando decisiones una regla a la vez.
Solo biblioteca estándar, sin modelos, sin red; no guarda texto de mensajes (solo el identificador de la regla que decidió y la marca).
Cómo decide: cada regla del enrutador («tarea sin señal clara», «pregunta por lo hablado», «comando pegado»…) acumula las marcas de las tareas que pasaron por ella (--marca v1|v2|ambas|ninguna = qué fuente aportó).
Una regla pasa a la acción más barata (ninguna < carpeta < conversaciones < las dos) cuya COBERTURA —la fracción de marcas que esa acción habría satisfecho— tenga un límite inferior de Wilson (95 % a una cola) ≥ 0.90.
Con marcas perfectas eso pide ≈ 25 por regla; con algún fallo, más. Hasta entonces la regla busca en las dos (modo «ambas») o, con BUSCADOR_PRIOR=reglas (o el archivo .context/enrutador-prior), usa su decisión original salvo que los datos la contradigan.
Sondeo: una de cada 10 veces una regla ya estrechada busca igual en las dos, para seguir midiendo lo que se perdería (sin sondeo la evidencia se sesgaría). Las reglas que no pueden buscar (saludo, imagen suelta, pedido vago) no se calibran.
Uso: python3.12 -I calibrar_enrutador.py --estado [--uso ARCHIVO --marcas ARCHIVO]"""
import hashlib, json, math, os, re, sys
from pathlib import Path

Z = 1.645; OBJETIVO = float(os.environ.get("BUSCADOR_COBERTURA", "0.90")); SONDEO = 0.10
COSTO = {"ninguna": 0, "v1": 490, "v2": 580, "ambas": 1040}; ORDEN = ["ninguna", "v1", "v2", "ambas"]
CUBRE = {"ninguna": {"ninguna"}, "v1": {"v1", "ninguna"}, "v2": {"v2", "ninguna"}, "ambas": {"v1", "v2", "ambas", "ninguna"}}
FUENTE_A_ACCION = {"carpeta": "v1", "conversaciones": "v2", "ambas": "ambas"}; ACCION_A_FUENTE = {"v1": "carpeta", "v2": "conversaciones", "ambas": "ambas"}
FIJAS = ("saludo", "seguimiento", "sin contenido", "pedido vago", "solo una imagen", "imagen sin nombre", "texto pegado sin contenido")  # no pueden buscar o no hay nada que calibrar: se respetan siempre


def regla_id(motivo):
    """Identificador estable de la regla a partir del motivo (sin lo variable: «tema…», IDs, la nota «calibrado»)."""
    m = re.sub(r"\s*·\s*calibrado.*$", "", motivo or ""); m = re.sub(r"«[^»]*»", "«»", m); m = re.sub(r"inicio de tarea con .*", "inicio de tarea con referencias", m); return m.strip()[:90]


def prior_por_omision():
    """«ambas» (público: arranca en V1 + V2) salvo que BUSCADOR_PRIOR o el archivo .context/enrutador-prior del proyecto digan «reglas» (parte de las decisiones validadas del enrutador)."""
    v = os.environ.get("BUSCADOR_PRIOR")
    if not v:
        try: v = (Path(__file__).resolve().parents[2] / ".context" / "enrutador-prior").read_text(encoding="utf-8").strip()
        except OSError: v = "ambas"
    return v if v in ("ambas", "reglas") else "ambas"


def es_fija(rid): return rid.startswith(FIJAS)


def accion_original(d): return "ninguna" if not d.get("buscar") else FUENTE_A_ACCION[d["fuente"]]


def wilson_inferior(s, n):
    if n <= 0: return 0.0
    p = s / n; return (p + Z * Z / (2 * n) - Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / (1 + Z * Z / n)


def evidencia(filas, marcas):
    """{regla: [marcas válidas]}. Una marca vale si la búsqueda corrió en las dos fuentes (información completa) o si muestra una FALLA de una acción más estrecha (la marca no estaba cubierta)."""
    mk = {m["id"]: m["marca"] for m in marcas}; ev = {}
    for f in filas:
        m = mk.get(f.get("id"))
        if m is None: continue
        rid = f.get("regla") or regla_id(f.get("motivo", "")); ej = f.get("accion") or accion_original({"buscar": f.get("buscar"), "fuente": f.get("fuente")})
        if ej == "ambas" or m not in CUBRE[ej]: ev.setdefault(rid, []).append(m)
    return ev


def cobertura(obs, accion): return sum(1 for m in obs if m in CUBRE[accion])


def accion_vigente(rid, obs, original, prior="ambas"):
    """(acción, nota). Acción = la más barata elegible; si ninguna lo es, la de arranque (las dos, o la original con prior «reglas»)."""
    n = len(obs)
    if es_fija(rid): return original, "regla fija"
    for a in ORDEN:
        if wilson_inferior(cobertura(obs, a), n) >= OBJETIVO: return a, f"calibrada: {n} marcas, cobertura ≥ {wilson_inferior(cobertura(obs, a), n):.2f}"
    if prior == "reglas":
        if n >= 8 and cobertura(obs, original) / n < 0.70: return "ambas", f"la regla original falla ({cobertura(obs, original)}/{n}): se amplía a las dos"
        return original, f"sin evidencia suficiente ({n} marcas): decisión original"
    return "ambas", f"arranque: {n} de ≈ 25 marcas para calibrar esta regla"


def _sondeo(rid, k):
    return int(hashlib.sha1(f"{rid}:{k}".encode()).hexdigest(), 16) % 1000 < SONDEO * 1000


def aplicar(d, filas, marcas, prior=None):
    """Ajusta la decisión del enrutador `d` con la evidencia. Devuelve una copia con regla, acción, sondeo y nota de calibrado."""
    prior = prior or prior_por_omision(); out = dict(d); rid = regla_id(d["motivo"]); orig = accion_original(d); obs = evidencia(filas, marcas).get(rid, [])
    a, nota = accion_vigente(rid, obs, orig, prior); sondeo = False
    if a != "ambas" and not es_fija(rid) and _sondeo(rid, len(filas)): a, sondeo = "ambas", True; nota += " · sondeo (se busca en las dos para seguir midiendo)"
    out.update({"regla": rid, "original": orig, "accion": a, "sondeo": sondeo, "calibracion": nota})
    if a != orig:
        out["motivo"] = d["motivo"] + f" · calibrado: {a}"
        if a == "ninguna": out.update({"buscar": False, "fuente": None, "k": 0, "rutas": False, "tokens_aprox": 0})
        else: out.update({"buscar": True, "fuente": ACCION_A_FUENTE[a], "k": 3 if a != "v1" else 5 if d.get("rutas") else 3, "rutas": False, "tokens_aprox": COSTO[a]})
    return out


def estado(filas, marcas, prior=None):
    prior = prior or prior_por_omision(); ev = evidencia(filas, marcas); L = []
    total = sum(len(v) for v in ev.values()); L.append(f"Calibración del enrutador · prior «{prior}» · objetivo de cobertura {OBJETIVO:.2f} · {len(filas)} búsquedas registradas, {sum(1 for _ in marcas)} marcas ({total} con información válida)")
    L.append(f"{'regla':<62}{'n':>4}  {'ninguna':>7} {'v1':>4} {'v2':>4} {'ambas':>5}  acción vigente")
    reglas = sorted({f.get('regla') or regla_id(f.get('motivo', '')) for f in filas}, key=lambda r: -len(ev.get(r, [])))
    for r in reglas:
        obs = ev.get(r, []); orig = next((f.get('original') for f in reversed(filas) if (f.get('regla') or regla_id(f.get('motivo', ''))) == r and f.get('original')), 'ambas'); a, nota = accion_vigente(r, obs, orig, prior); c = {k: obs.count(k) for k in ("ninguna", "v1", "v2", "ambas")}
        L.append(f"{r[:60]:<62}{len(obs):>4}  {c['ninguna']:>7} {c['v1']:>4} {c['v2']:>4} {c['ambas']:>5}  {a} ({nota})")
    return "\n".join(L)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] != ["--estado"]: print(__doc__); sys.exit(0)
    base = Path(__file__).resolve().parents[2] / "datos"; g = lambda k, d: Path(a[a.index(k) + 1]) if k in a else d
    rd = lambda p: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []
    print(estado(rd(g("--uso", base / "uso_enrutador.jsonl")), rd(g("--marcas", base / "uso_enrutador_marcas.jsonl"))))
