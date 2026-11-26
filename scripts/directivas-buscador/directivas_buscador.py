#!/usr/bin/env python3.12
"""Buscador de directivas y memorias para Claude Code (hook por mensaje).

  directivas_buscador.py mapa            regenera .context/directivas-mapa.md (nucleo integro + una fila por directiva)
  directivas_buscador.py hook            hook UserPromptSubmit: lee el JSON de stdin e inyecta las directivas afines
  directivas_buscador.py buscar "texto"  prueba a mano (imprime titulos, puntajes y tamano de la inyeccion)
  directivas_buscador.py guarda          compara directivas contra mapa (avisa si hay desfase)

Se corre siempre con: python3 -I <este archivo> <comando>
Detalle: README.md y docs/
"""
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRECTIVAS = os.path.join(RAIZ, ".context", "directivas.md")
MAPA = os.path.join(RAIZ, ".context", "directivas-mapa.md")
DISPARADORES = os.path.join(RAIZ, ".context", "directivas-disparadores.tsv")
BASE = os.environ.get("BUSCADOR_HOME") or os.path.expanduser("~/.memoria-local")
ESTADO_DIR = os.path.join(BASE, "directivas-estado")
MEM_DIR = os.path.expanduser(os.path.join("~/.claude/projects", re.sub(r"[^A-Za-z0-9]", "-", RAIZ), "memory"))
STEM_VOCAL = False      # raíz ligera: quita la vocal final (conjugaciones y plurales)
REL_MIN_MEM = 0.70    # una memoria debe tener al menos esta fracción del mejor puntaje de memorias (0.75 hasta 2026-11-25)
CAP_SESION = 60000     # tope de caracteres de texto completo inyectados por sesión (~20 mil tokens); al agotarse solo se dan punteros
CAP_TOTAL_SESION = 90000  # tope duro de todo lo inyectado por sesión (~30 mil tokens); al agotarse el hook calla (quedan el mapa y la directiva 00)
TOP_K_MEM = 2
CAP_MEM = 1800        # caracteres de una memoria inyectada completa
ABS_MIN_MEM = 6.0     # puntaje minimo de una memoria (se calibra con evaluacion/memoria_consultas.tsv)
BONO_SLUG_MEM = 3.0   # por cada palabra del mensaje que está en el nombre (slug) de la memoria; solo memorias (2026-11-25)

TOP_K = 3
CAP_TEXTO = 6000      # caracteres de una directiva inyectada completa (2,600 hasta 2026-11-25: cortaba 14 de 88 directivas, entre ellas la 0 ter; ahora es una red de seguridad: la más larga mide 4,935 sin procedencia)
CAP_TOTAL = 8000      # tope de la inyeccion por mensaje
BONO_DISPARADOR = 4.0  # por cada palabra del mensaje que coincide con los disparadores curados de la directiva
REL_MIN = 0.55        # un resultado debe tener al menos esta fraccion del mejor puntaje
ABS_MIN = 6.5         # puntaje minimo absoluto (sin senal, no se inyecta nada)

STOP = set("""
de la el los las un una unos unas y o u e a al del en con por para que se su sus lo le les me mi mis te tu tus nos
es son ser fue ha han hay he has este esta esto estos estas ese esa eso esos esas aqui alli ahi ya si no mas menos muy
como cuando donde cual cuales quien pero sino sobre entre hasta desde solo tambien todo toda todos todas cada otro otra
ver dame dime damela dar hacer hace hacen haz quiero necesito puedes puede podemos vamos va ok bien listo gracias
the and for nuevo nueva nuevos crea crear arma hazme quiero ahora mismo voy cambio cambios mejora mejoras mejorar aplica aplicar necesarias necesario registro seguir saber final tabla comparativa luego despues antes
""".split())


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


SIGLAS_2 = {s for s in os.environ.get("BUSCADOR_SIGLAS", "").lower().replace(" ", "").split(",") if s}  # siglas de dos letras que cuentan como palabra (solo al buscar memorias; por defecto ninguna)


def toks(t, siglas=False):
    out = []
    for w in re.findall(r"[a-z0-9_]{2,}", norm(t)):
        if len(w) == 2 and not (siglas and w in SIGLAS_2):
            continue
        if w in STOP:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        if STEM_VOCAL and len(w) > 4 and w[-1] in "aeo":  # pega/pegó/pegar -> peg; clave/claves -> clav
            w = w[:-1]
        out.append(w[:6] if len(w) > 6 else w)
    return out


def es_encabezado(l):
    return len(l) < 120 and re.match(r"^\*\*\d+( bis)?\. .*\*\*$", l) is not None


def titulo(l):
    m = re.match(r"^- \*\*(.+?)\*\*", l) or re.match(r"^\*\*(.+?)\*\*", l)
    if m:
        t = m.group(1)
    else:
        t = re.sub(r"^- ", "", l)
        t = re.split(r"(?<=[.:;]) ", t)[0]
    t = re.sub(r"\s+", " ", t).strip(" *_")
    return t if len(t) <= 120 else t[:117].rstrip() + "..."


def cargar():
    """Devuelve (unidades, nucleo_lineas). unidad = dict(n, parent, titulo, texto, header)."""
    with open(DIRECTIVAS, encoding="utf-8") as f:
        L = f.read().split("\n")
    inicio = next(i for i, l in enumerate(L) if l.startswith("**00."))
    unidades, parent, nucleo = [], "", []
    sec_actual = None
    for i in range(inicio, len(L)):
        l = L[i].rstrip()
        n = i + 1
        if not l.strip():
            continue
        if l.startswith("## "):
            parent = "general"  # directivas bajo un encabezado «## » (sin número de sección)
            sec_actual = None
            continue
        if es_encabezado(l):
            m = re.match(r"^\*\*(\d+)", l)
            parent = "§" + m.group(1)
            sec_actual = m.group(1) if m.group(1) in ("2", "3") else None
            if sec_actual:
                nucleo.append((n, l))
            continue
        if sec_actual:
            nucleo.append((n, l))
        prioritaria = re.match(r"^\*\*(00|P[1-4])\. ", l) is not None  # P1-P4: las tres alertas (2026-11-23)
        if prioritaria:
            nucleo.append((n, l))
        if "[ELIMINADA" in l or "(Retirada" in l:
            continue
        if parent == "" and l.startswith("**"):
            parent = "§0"
        unidades.append({"n": n, "parent": parent or "§0", "titulo": titulo(l), "texto": l,
                         "nucleo": bool(sec_actual) or prioritaria})
    return unidades, sorted(set(nucleo))


def generar_mapa():
    unidades, nucleo = cargar()
    ahora = time.strftime("%Y-%m-%d %H:%M")
    out = [
        "# Mapa de directivas (Tier 1, siempre cargado)",
        "",
        f"_(generado {ahora} por `scripts/directivas-buscador/directivas_buscador.py mapa` desde `.context/directivas.md`; no editar a mano, se regenera solo)_",
        "",
        "**Antes de cada respuesta o acción: ¿lo que voy a hacer cae en alguna fila de abajo?** Si cae, leer ESE apartado completo en `.context/directivas.md` (la línea `L<n>` indica dónde; `Read` con `offset` y `limit` 1) y seguirlo al pie de la letra. Un hook (`UserPromptSubmit`) ya inyecta el texto de las directivas más afines a cada mensaje del usuario, pero no sustituye este repaso. Manda la última orden explícita del usuario en el chat.",
        "",
        "## Núcleo (texto íntegro: directiva máxima, las tres alertas prioritarias P1 a P4, escrituras y credenciales)",
        "",
    ]
    for n, l in nucleo:
        out.append(l)
    out += ["", "## Mapa (una fila por directiva: línea · sección · regla)", ""]
    for u in unidades:
        if u["nucleo"]:
            continue
        out.append(f"- L{u['n']} · {u['parent']} · {u['titulo']}")
    out.append("")
    with open(MAPA, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return len(unidades), os.path.getsize(MAPA)


def disparadores():
    out = []
    try:
        for l in open(DISPARADORES, encoding="utf-8"):
            if "\t" in l and not l.startswith("#"):
                a, b = l.rstrip("\n").split("\t", 1)
                out.append((norm(a), b))
    except OSError:
        pass
    return out


def extra(u, disp):
    nt = norm(u["titulo"] + " " + u["texto"][:200])
    return " ".join(b for a, b in disp if a in nt)


def indice(unidades, siglas=False):
    docs = []
    trigs = []
    disp = disparadores()
    for u in unidades:
        trigs.append(set(toks(extra(u, disp), siglas)))
        frases = re.findall(r"«([^»]{4,80})»", u["texto"])
        t = (u["titulo"] + " ") * 3 + " ".join(frases) * 2 + " " + (extra(u, disp) + " ") * 3 + u["texto"]
        docs.append(toks(t, siglas))
    N = len(docs)
    avg = sum(len(d) for d in docs) / N
    df = {}
    for d in docs:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    return docs, df, avg, trigs


def puntuar(q, unidades, docs, df, avg, trigs, k1=1.5, b=0.4, siglas=False, bono_slug=0.0):
    N = len(docs)
    qs = set(toks(q, siglas))
    res = []
    for u, d, tg in zip(unidades, docs, trigs):
        if u["nucleo"]:
            continue
        tf = {}
        for w in d:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in qs:
            if w in tf:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
        s += BONO_DISPARADOR * len(qs & tg)
        if s > 0 and bono_slug:
            s += bono_slug * len(qs & set(toks(u.get("slug", ""), siglas)))
        if s > 0:
            res.append((s, u))
    res.sort(key=lambda x: -x[0])
    return res


def seleccionar(res, abs_min=None, top_k=None, rel_min=None):
    abs_min = ABS_MIN if abs_min is None else abs_min
    top_k = TOP_K if top_k is None else top_k
    if not res or res[0][0] < abs_min:
        return []
    top = res[0][0]
    rel = REL_MIN if rel_min is None else rel_min
    return [(s, u) for s, u in res[:top_k] if s >= rel * top and s >= abs_min]


def cargar_memoria():
    """Memorias de Claude (archivos del directorio de memoria, sin MEMORY.md) como unidades de busqueda."""
    us = []
    try:
        nombres = sorted(os.listdir(MEM_DIR))
    except OSError:
        return us
    for fn in nombres:
        if not fn.endswith(".md") or fn == "MEMORY.md":
            continue
        try:
            t = open(os.path.join(MEM_DIR, fn), encoding="utf-8").read()
        except OSError:
            continue
        name = desc = ""
        body = t
        if t.startswith("---\n"):
            fin = t.find("\n---", 4)
            if fin > 0:
                fm = t[4:fin]
                body = t[fin + 4:].lstrip("\n")
                m = re.search(r"^name:\s*(.+)$", fm, re.M)
                name = m.group(1).strip() if m else ""
                m = re.search(r"^description:\s*(.+)$", fm, re.M)
                desc = m.group(1).strip() if m else ""
        slug = name or fn[:-3]
        us.append({"n": fn, "parent": "M", "titulo": slug.replace("-", " ") + " " + desc, "texto": body, "nucleo": False, "slug": slug})
    return us


def frases_citadas(t):
    """Frases entre « », “ ” o comillas rectas (4 a 80 caracteres), normalizadas."""
    return {" ".join(norm(f).split()) for g in re.findall(r"«([^»]{4,80})»|“([^”]{4,80})”|\"([^\"]{4,80})\"", t) for f in g if f}


def seleccionar_mem(res, prompt, umbral=None):
    """Memorias a inyectar: las mejores por puntaje y, además, una cuya frase entrecomillada coincide con una del mensaje (p. ej. «Tus servicios»), aunque no llegue al tope por puntaje (2026-11-25)."""
    umbral = ABS_MIN_MEM if umbral is None else umbral
    sel = seleccionar(res, umbral, TOP_K_MEM, REL_MIN_MEM)
    fq = frases_citadas(prompt)
    if not fq:
        return sel
    ya = {u["n"] for s, u in sel}
    for s, u in res:
        if s < umbral:
            break
        if u["n"] not in ya and fq & frases_citadas(u["titulo"] + " " + u["texto"]):
            return sel + [(s, u)]
    return sel


def formato_mem(sel, vistas, solo_punteros=False):
    if not sel:
        return "", []
    partes = ["[Memorias relevantes (automático); los archivos están en ~/.claude/projects/<proyecto>/memory/]"]
    nuevas = []
    for s, u in sel:
        clave = "m:" + u["n"]
        if clave in vistas or solo_punteros:
            partes.append(f"• memoria {u['slug']} ({u['n']}; {'tope de texto de la sesión alcanzado' if solo_punteros and clave not in vistas else 'ya inyectada antes en esta sesión'})")
            continue
        t = u["texto"].strip()
        if len(t) > CAP_MEM:
            t = t[:CAP_MEM].rstrip() + f" … [recortada; archivo completo: {u['n']}]"
        partes.append(f"• memoria {u['slug']} ({u['n']})\n{t}")
        nuevas.append(clave)
    return "\n".join(partes), nuevas


PROV = re.compile(r"\s*_\((?:[^()]|\([^()]*\))*\)_")  # «_( procedencia: fecha, por qué la dictó, cita textual )_»


def sin_procedencia(t):
    """Quita de lo INYECTADO las notas de procedencia (21 % del texto de las directivas; siguen completas en directivas.md) y deja una sola marca (2026-11-25)."""
    n = [0]

    def f(m):
        n[0] += 1
        return " _(procedencia omitida aquí; está en el archivo)_" if n[0] == 1 else ""
    return PROV.sub(f, t)


def formato(sel, vistas, solo_punteros=False):
    partes = ["[Buscador de directivas, automático: las más afines a este mensaje. Léelas ANTES de responder; el mapa completo está en CLAUDE.md.]"]
    total = len(partes[0])
    nuevas = []
    for s, u in sel:
        if u["n"] in vistas or solo_punteros:
            partes.append(f"• L{u['n']} · {u['titulo']} ({"tope de texto de la sesión alcanzado" if solo_punteros and u["n"] not in vistas else "ya inyectada antes en esta sesión"}; texto en .context/directivas.md línea {u['n']})")
            continue
        t = sin_procedencia(u["texto"])
        if len(t) > CAP_TEXTO:
            t = t[:CAP_TEXTO].rstrip() + f" … [recortada aquí; texto completo: .context/directivas.md línea {u['n']}]"
        bloque = f"• L{u['n']} · {u['parent']}\n{t}"
        if total + len(bloque) > CAP_TOTAL:
            partes.append(f"• L{u['n']} · {u['titulo']} (texto en .context/directivas.md línea {u['n']})")
        else:
            partes.append(bloque)
            total += len(bloque)
            nuevas.append(u["n"])
    return "\n".join(partes), nuevas


def mapa_desactualizado():
    try:
        return os.path.getmtime(MAPA) < os.path.getmtime(DIRECTIVAS)
    except OSError:
        return True


def hook():
    try:
        datos = json.load(sys.stdin)
    except Exception:
        return
    prompt = (datos.get("prompt") or "")[:2000]
    sid = re.sub(r"[^A-Za-z0-9_-]", "", datos.get("session_id") or "sin-sesion")
    if mapa_desactualizado():
        generar_mapa()
    unidades, _ = cargar()
    docs, df, avg, trigs = indice(unidades)
    sel = seleccionar(puntuar(prompt, unidades, docs, df, avg, trigs))
    mu = cargar_memoria()
    msel = []
    if mu:
        mdocs, mdf, mavg, mtrigs = indice(mu, True)
        msel = seleccionar_mem(puntuar(prompt, mu, mdocs, mdf, mavg, mtrigs, siglas=True, bono_slug=BONO_SLUG_MEM), prompt)
    if not sel and not msel:
        return
    os.makedirs(ESTADO_DIR, mode=0o700, exist_ok=True)
    ruta = os.path.join(ESTADO_DIR, sid + ".json")
    try:
        with open(ruta) as f:
            dato = json.load(f)
        vistas, total, gastados = (set(dato), 0, 0) if isinstance(dato, list) else (set(dato.get("v", [])), int(dato.get("c", 0)), int(dato.get("t", 0)))
    except Exception:
        vistas, total, gastados = set(), 0, 0
    if total >= CAP_TOTAL_SESION:
        return
    solo = gastados >= CAP_SESION
    texto, nuevas = formato(sel, vistas, solo) if sel else ("", [])
    tm, nm = formato_mem(msel, vistas, solo)
    if tm:
        texto = (texto + "\n\n" + tm) if texto else tm
    nuevas = nuevas + nm
    vistas.update(nuevas)
    with open(ruta, "w") as f:
        json.dump({"v": list(vistas), "c": total + len(texto), "t": gastados + (len(texto) if nuevas else 0)}, f)
    for fn in os.listdir(ESTADO_DIR):
        p = os.path.join(ESTADO_DIR, fn)
        if time.time() - os.path.getmtime(p) > 7 * 86400:
            os.remove(p)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": texto}}, ensure_ascii=False))


def buscar(q):
    unidades, _ = cargar()
    docs, df, avg, trigs = indice(unidades)
    res = puntuar(q, unidades, docs, df, avg, trigs)
    sel = seleccionar(res)
    print(f"consulta: {q!r}  tokens: {sorted(set(toks(q)))}")
    for s, u in res[:6]:
        marca = "*" if (s, u) in sel else " "
        print(f" {marca} {s:6.1f}  L{u['n']:<4} {u['parent']:<8} {u['titulo'][:100]}")
    texto, _ = formato(sel, set()) if sel else ("", [])
    print(f"  -> inyeccion: {len(texto)} caracteres (~{len(texto)//3} tokens), {len(sel)} directivas")


def evalmem(umbral=None):
    """Mide la recuperacion de memorias: aciertos con las consultas con memoria esperada y disparos falsos con las marcadas «-»."""
    mu = cargar_memoria()
    docs, df, avg, trigs = indice(mu, True)
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluacion", "memoria_consultas.tsv")
    casos = [l.rstrip("\n").split("\t") for l in open(ruta, encoding="utf-8") if l.strip()]
    umbral = ABS_MIN_MEM if umbral is None else umbral
    h1 = h3 = n = disp = 0
    malas = []
    fals = []
    for q, rx in casos:
        res = puntuar(q, mu, docs, df, avg, trigs, siglas=True, bono_slug=BONO_SLUG_MEM)
        sel = seleccionar_mem(res, q, umbral)
        if q == "-":
            continue
        if rx == "":
            continue
        if not any(re.search(rx, u["n"]) for u in mu):
            malas.append(("sin memoria esperada", q)); continue
        n += 1
        pos = next((i + 1 for i, (s, u) in enumerate(res) if re.search(rx, u["n"])), None)
        h1 += pos == 1
        h3 += bool(pos and pos <= 3)
        if any(re.search(rx, u["n"]) for s, u in sel):
            disp += 1
        else:
            malas.append((f"pos={pos} top1={res[0][1]['n'] if res else '-'} punt={res[0][0]:.1f}" if res else "sin resultados", q))
    for q, rx in casos:
        if q == "-" or rx == "":
            pass
    neg = [rx for q, rx in casos if q == "-"]
    for t in neg:
        sel = seleccionar_mem(puntuar(t, mu, docs, df, avg, trigs, siglas=True, bono_slug=BONO_SLUG_MEM), t, umbral)
        if sel:
            fals.append((t, [u["n"] for s, u in sel]))
    print(f"memorias: {len(mu)}  consultas con memoria esperada: {n}  umbral: {umbral}")
    print(f"  hit@1={h1/n:.0%}  hit@3={h3/n:.0%}  se inyecta la correcta (umbral y top {TOP_K_MEM})={disp/n:.0%}")
    print(f"  disparos falsos en {len(neg)} mensajes genéricos: {len(fals)}  {fals[:4]}")
    for m in malas[:12]:
        print("   falla:", m)


def compactar_memoria(aplicar=False):
    """Deja MEMORY.md en forma CORTA (2026-11-25): «- archivo.md» por memoria (si el título difiere del nombre del archivo, «- archivo.md — título»), sin gancho: el hook trae el cuerpo de las afines.
    Acepta la forma larga «- [titulo](archivo.md) — gancho» (la que escribe Claude por defecto) y la normaliza; verifica que la lista de archivos quede idéntica, mantiene una línea de formato al inicio
    y reemplaza el archivo de forma atómica (temporal + os.replace)."""
    ruta = os.path.join(MEM_DIR, "MEMORY.md")
    texto = open(ruta, encoding="utf-8").read()
    cab = "<!-- Formato corto: «- archivo.md» (título solo si difiere). Si agregas una memoria como «[título](archivo.md) — gancho», normaliza con: python3.12 -I scripts/directivas-buscador/directivas_buscador.py memoria --aplicar -->"
    largo = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\)(?: — .*)?$")
    corto = re.compile(r"^- ([^\s\[\]()]+\.md)(?: — .*)?$")

    def refs(s):
        r = []
        for l in s.split("\n"):
            m = largo.match(l)
            if m: r.append(m.group(2))
            else:
                m = corto.match(l)
                if m: r.append(m.group(1))
        return r
    out = []
    for l in texto.split("\n"):
        if l.startswith("<!-- Formato corto"):
            continue
        m = largo.match(l)
        if m:
            tit, arch = m.group(1), m.group(2)
            out.append(f"- {arch}" if tit == arch[:-3] else f"- {arch} — {tit}")
        else:
            out.append(l)
    nuevo = cab + "\n" + "\n".join(out)
    if refs(texto) != refs(nuevo):
        print("ABORTA: la lista de archivos no coincide"); return 1
    archivos = {f for f in os.listdir(MEM_DIR) if f.endswith(".md") and f != "MEMORY.md"}
    enlaces = set(refs(nuevo))
    print(f"MEMORY.md: {len(texto.encode())} -> {len(nuevo.encode())} bytes (~{len(texto.encode())//3} -> ~{len(nuevo.encode())//3} tokens); entradas {len(refs(nuevo))}; "
          f"archivos de memoria sin entrada: {sorted(archivos - enlaces)}; entradas sin archivo: {sorted(enlaces - archivos)}")
    if aplicar and nuevo != texto:
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(nuevo)
        os.replace(tmp, ruta)
        print("aplicado")
    return 0


def actualizar(fase, tema=""):
    """Partes mecánicas del protocolo «actualizar directivas» (docs/protocolo-actualizar-directivas.md).
    antes <tema>: respaldo de directivas.md.  despues: mapa, guarda, memoria compacta, evaluación de memorias y directivas sin disparadores."""
    import shutil
    if fase == "antes":
        slug = re.sub(r"[^a-z0-9]+", "-", norm(tema)).strip("-") or "sin-tema"
        dest = os.path.join(RAIZ, "respaldos", f"directivas-antes-{slug}-{time.strftime('%Y-%m-%d')}.md")
        shutil.copy2(DIRECTIVAS, dest)
        print(f"respaldo: {os.path.relpath(dest, RAIZ)} ({os.path.getsize(dest)} bytes)")
        return 0
    if fase == "despues":
        n, b = generar_mapa()
        print(f"mapa: {n} directivas, {b} bytes (~{b//3} tokens)")
        rc = guarda()
        compactar_memoria(True)
        evalmem()
        unidades, _ = cargar()
        disp = disparadores()
        sin = [u for u in unidades if not u["nucleo"] and not extra(u, disp)]
        print(f"directivas sin disparadores: {len(sin)}; las 5 últimas: " + "; ".join(f"L{u['n']} {u['titulo'][:50]}" for u in sin[-5:]))
        print("falta a mano: memoria (archivo + línea en MEMORY.md), registro de cambios, línea en .context/changelog.md y anti-patterns.md si nace de un error")
        return rc
    print("uso: actualizar antes <tema> | actualizar despues")
    return 2


def guarda():
    unidades, _ = cargar()
    if not os.path.exists(MAPA):
        print("MAPA NO EXISTE"); return 1
    filas = sum(1 for l in open(MAPA, encoding="utf-8") if re.match(r"^- L\d+ · ", l))
    huerf = [a for a, _ in disparadores() if not any(a in norm(u["titulo"] + " " + u["texto"][:200]) for u in unidades)]
    for h in huerf:
        print(f"  disparador sin directiva: {h!r}")
    try:
        punteros = set(re.findall(r"historial (H-\d+)", open(DIRECTIVAS, encoding="utf-8").read()))
        entradas = set(re.findall(r"^### (H-\d+) ", open(os.path.join(RAIZ, ".context", "directivas-historial.md"), encoding="utf-8").read(), re.M))
    except OSError:
        punteros, entradas = set(), set()
    print(f"  historial: {len(entradas)} entradas, {len(punteros)} punteros; " + ("coinciden" if punteros == entradas else f"DESFASE punteros sin entrada {sorted(punteros - entradas)}, entradas sin puntero {sorted(entradas - punteros)}"))
    ok = filas == len([u for u in unidades if not u["nucleo"]]) and not mapa_desactualizado() and not huerf and punteros == entradas
    try:
        r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "hook"], input=json.dumps({"session_id": "humo-guarda", "prompt": "voy a correr un ALTER TABLE en produccion"}),
                           capture_output=True, text=True, timeout=20)
        humo = "hook OK" if "additionalContext" in r.stdout else "HOOK SIN SALIDA"
        os.remove(os.path.join(ESTADO_DIR, "humo-guarda.json"))
    except Exception as e:
        humo = f"HOOK FALLA ({e})"
    errs = os.path.join(ESTADO_DIR, "errores.log")
    print(f"  prueba de humo: {humo}; errores registrados: {sum(1 for _ in open(errs)) if os.path.exists(errs) else 0}")
    print(f"directivas: {len(unidades)}  filas del mapa: {filas}  mapa {'al dia' if not mapa_desactualizado() else 'DESACTUALIZADO'}  -> {'OK' if ok else 'DESFASE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "mapa":
            n, b = generar_mapa(); print(f"mapa: {n} directivas, {b} bytes (~{b//3} tokens)")
        elif cmd == "hook":
            hook()
        elif cmd == "buscar":
            buscar(" ".join(sys.argv[2:]))
        elif cmd == "actualizar":
            sys.exit(actualizar(sys.argv[2] if len(sys.argv) > 2 else "", " ".join(sys.argv[3:])))
        elif cmd == "memoria":
            sys.exit(compactar_memoria("--aplicar" in sys.argv))
        elif cmd == "evalmem":
            evalmem(float(sys.argv[2]) if len(sys.argv) > 2 else None)
        elif cmd == "guarda":
            sys.exit(guarda())
        else:
            print(__doc__)
    except Exception as e:  # el hook nunca debe romper la sesion, pero deja rastro del error
        if cmd in ("hook",):
            try:
                import traceback
                os.makedirs(ESTADO_DIR, mode=0o700, exist_ok=True)
                with open(os.path.join(ESTADO_DIR, "errores.log"), "a") as lg:
                    lg.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + traceback.format_exc().strip().splitlines()[-1] + "\n")
            except Exception:
                pass
            sys.exit(0)
        raise
