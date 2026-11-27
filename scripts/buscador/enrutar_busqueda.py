"""ENRUTADOR DE BÚSQUEDA (2026-11-27): implementa el criterio de docs/criterio-busqueda.md con señales OBSERVABLES del pedido; solo biblioteca estándar, sin modelos, sin red.
decidir(mensaje) → {buscar, fuente: carpeta|conversaciones|ambas, k, rutas, urgente, motivo, tokens_aprox}.
Reglas (en este orden): 1) saludos y respuestas cortas, seguimientos cortos de la tarea en curso («súbelo»), y pedidos GENÉRICOS sin nada del proyecto → no se busca; 2) urgencia («YA», «apúrate», «urgente»…) → modo ligero solo para esa búsqueda;
3) señales de LO HABLADO (verbos de pasado con el usuario, fechas, «¿qué decidimos?», o una pregunta en pasado en general) → conversaciones; señales de LO ESCRITO («¿dónde está…?», «¿qué doc…?», «¿en qué archivo…?») → carpeta (solo rutas si basta ubicar el archivo); ambas señales o ninguna → las dos;
4) tamaño: 2 resultados si lo buscado es exacto (ID, archivo, error literal, texto entre comillas); si no, 3. Costos medidos (tokens de salida): ambas k3 ≈ 1,040 · ambas k2 ≈ 730 · conversaciones ≈ 580 · carpeta ≈ 490 · rutas ≈ 330.
Patrones genéricos; BUSCADOR_ID_PATRON agrega el de tus tickets. Las listas están a propósito al inicio del archivo para ajustarlas a otro idioma o equipo."""
import os, re, unicodedata
from pathlib import Path

TOKENS = {"ambas3": 1040, "ambas2": 730, "conversaciones": 580, "carpeta": 490, "rutas": 330, "nada": 0}


def norm(s): return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


SALUDO = re.compile(r"^\s*((hola|buenas|gracias|muchas gracias|ok|okey|vale|listo|perfecto|si|no|adelante|dale|bien|ya|claro|entendido|buenisimo|genial|excelente|super|nada mas)\b[\s.!¡?¿,]*)+$")
HABLADO = re.compile(r"\b(dijimos|dijiste|dije|decidimos|decidiste|decidi|hablamos|hablaste|comentamos|quedamos|acordamos|acordaste|pedi|pediste|te pedi|te mande|me mandaste|mandamos|corrimos|ejecutamos|ejecute|hicimos|hiciste|hice|armamos|armaste|arme|propusiste|propuse|revisamos|vimos|mencionaste|mencione|explicaste|respondiste|contestaste|aplicamos|aplicaste|cambiamos|cambiaste|corregimos|resolvimos|recuerdas|te acuerdas|me acuerdo|no me acuerdo|la vez pasada|otra vez|como antes|retomemos|retomar|seguimos con)\b|\bque (se )?(decidio|dijo|paso|quedo|hicimos|corrimos|acordamos)\b|\bpor que (quedo|lo hicimos|elegimos|decidimos)\b|\b(ayer|anteayer|antier|semana pasada|mes pasado|hace \d+ (dias|semanas|meses)|el \d{1,2} de [a-z]+)\b|\bque (query|consulta|comando|sql) (corrimos|ejecutamos|usamos|hicimos)\b")
ESCRITO = re.compile(r"\b(donde (esta|queda|vive|se (guarda|documento|anoto))|en que (archivo|doc|documento|carpeta|ruta|script|modulo)|que (doc|documento|archivo|directiva|memoria|nota|script) |cual es (el|la) (doc|documento|archivo|ruta|directiva|script)|como (esta|quedo) documentad[oa]|esta documentad[oa]|hay (un )?(doc|documento|trazabilidad)|ya hay (un )?(doc|documento|trazabilidad)|ruta de|trazabilidad|directiva)\b")
PASADO_MORFO = re.compile(r"\b\w{3,}(amos|imos|aste|iste|aba|abamos|abas|aban|iamos|ian)\b|\b(habia|tenia|decia|sabia|queria|podia|hacia|veia|iba|era|eran|fue|fueron|quedo|quedaron|paso|salio|dio|dijo|pidio|llego|sumaba|faltaba|correspondia)\b")  # pasado en general (nosotros, tú, imperfecto y algunos irregulares)
INTERROGATIVA = re.compile(r"^\s*¿|\?\s*$|(^|[,;:]\s*)¿?(que|cual|cuales|cuanto|cuantos|cuantas|quien|quienes|cuando|donde|como|por que|a que|en que|para que|con que|de que|a quien|a cuantos)\b")
REFPREVIA = re.compile(r"\b(eso de|lo de|lo del|lo que|aquello de|aquello que)\b")  # «lo de ayer», «eso de la precisión…»: el referente suele ser una conversación previa
UBICAR = re.compile(r"\b(en que (archivo|script|modulo)|que archivo|donde esta (el|la) (archivo|script|funcion|clase|modulo)|cual es la ruta|ruta de)\b")
GENERICO = re.compile(r"^\s*(ayudame a|dime (como|que|cual)|que buenas practicas|recomiendame|sugiereme|explica(me)?|como funciona|que (es|son|significa|diferencia hay)|dame (un )?(ejemplo|ideas)|escribe (una|un) (funcion|script|regex|expresion|correo|texto)|traduce|resume|convierte|cuanto es|como (puedo|hago|calculo|configuro|medir|se hace)|genera (una|un) (tabla|lista|plan)|arma (un|una) plan de estudio|optimiza (esta|este)|revisa este codigo)\b")
SEGUIMIENTO = re.compile(r"\b\w+(elo|ela|elos|elas|alo|ala|alos|alas|ilo|ila|ilos|ilas|olo|ola|ulo|ula|melo|telo|selo)\b")  # verbo + pronombre («súbelo», «revísalo», «aplícalo»): seguimiento de la tarea en curso
URGENTE_YA = re.compile(r"\bYA\b")  # «YA» en mayúsculas (sobre el texto original)
URGENTE = re.compile(r"\b(apurate|apurense|urgente|urgentemente|rapido|rapidito|de inmediato|lo necesito ya|ahorita mismo|cuanto antes)\b")  # sobre el texto sin acentos
REFS = {"id": r"\b[A-Za-z]{2,6}-\d{2,6}\b", "url": r"https?://[^\s)>\]]+", "ruta": r"(?:[\w.\-]+/)+[\w.\-]+\.\w{1,5}\b", "archivo": r"\b[\w\-]+\.(?:py|sql|md|csv|tsv|xlsx|docx|pptx|json|sh|yml|yaml|txt)\b",
        "cita": r"[«\"“`]([^»\"”`\n]{3,60})[»\"”`]", "error": r"\b\w+(?:Error|Exception)\b"}
NO_ID = {"SHA", "MD", "ISO", "RFC", "AES", "RSA", "UTF", "TLS", "SSL", "IPV", "GPT", "WPA", "USB", "PDF"}  # prefijos con guion y número que NO son tickets («SHA-256», «ISO-8601»)
EXACTO = ("id", "archivo", "cita", "error")  # referencias exactas: bastan 2 resultados

STOP_C = set("de del la las el los lo le les un una unos unas y o u a al en con por para que se me te nos mi tu su sus es son ser esta este esto eso ese esa estos estas no si ya mas muy como cual cuales cuando donde sobre entre desde hasta hay ha han he tiene tengo tienen tenemos fue era sin pero porque tambien solo".split())
INSTR = set("apoyame apoyar apoya apoyas ayudame ayudar ayuda ayudas necesito necesitamos necesitan quiero quisiera puedes podrias porfa favor please revisa revisar checa checar mira ver veamos requerimiento requerimientos solicitud solicitudes pedido pedidos tema temas asunto asuntos caso casos tarea tareas cosa cosas algo hola buenas buenos dias tardes noches".split())
CONECTORES = STOP_C | {"favor", "porfa"}
FRASE_INSTR = re.compile(r"^\s*(?:hola[,!]?\s*)?(?:por favor\s*|porfa\s*)?(?:apoyame|apoyarme|ayudame|ayudarme|echame una mano|me ayudas|me apoyas|puedes apoyarme|podrias ayudarme)\b[^:\n]{0,60}:\s*")
SIGUIENTE = "antes de buscar: mira el adjunto o lo último de la conversación; si no hay, revisa tus pendientes asignados (solo lectura) y haz UNA pregunta cerrada con candidatos; luego busca con los términos que salgan"


def palabras_contenido(texto):
    sig = [x for x in os.environ.get("BUSCADOR_SIGLAS", "").lower().replace(" ", "").split(",") if x]
    return [w for w in re.findall(r"[a-z0-9_]+", norm(re.sub(r"https?://\S+", " ", texto))) if w not in STOP_C and w not in INSTR and (len(w) >= 3 or w in sig or any(c.isdigit() for c in w))]


def especificos(texto):
    """Palabras que parecen nombres propios, siglas o identificadores (mayúscula a medio renglón, dígitos o guion bajo)."""
    n = 0
    for i, m in enumerate(re.finditer(r"\S+", texto)):
        w = m.group(0).strip(".,;:¿?¡!()«»\"'")
        if len(w) >= 3 and i > 0 and (w[0].isupper() or any(c.isdigit() for c in w) or "_" in w): n += 1
    return n


def limpiar_consulta(msg):
    """Quita las etiquetas de pegado y la instrucción inicial («apóyame con este requerimiento:») para que la consulta sea solo el contenido."""
    t = re.sub(r"</?pasted_content[^>]*>", " ", msg); t = re.sub(r"\[Image #\d+\]", " ", t); nt = norm(t); m = FRASE_INSTR.match(nt)
    if m and len(nt) == len(t): return t[m.end():].strip()
    toks = list(re.finditer(r"\S+", t)); i = 0
    while i < len(toks) and (norm(toks[i].group(0).strip(".,;:¿?¡!")) in INSTR or norm(toks[i].group(0).strip(".,;:¿?¡!")) in CONECTORES): i += 1
    return t[toks[i].start():].strip() if i < len(toks) else ""

HOWTO = re.compile(r"^\s*¿?\s*(hay|existe|existiria|habra)\s+(\w+\s+)?(forma|manera|modo)\s+de\b")  # «¿hay forma de…?»: pregunta general de cómo-hacer, se resuelve en la web
EXTERNO = re.compile(r"\b(checa|checar|revisa|revisar|lee|leer|verifica|verificar|mira|abre|consulta)\b[^.?!]{0,50}\b(slack|jira)\b|\b(pidio|pidieron|dijo|dijeron|comento|comentaron|escribio|escribieron|mando|mandaron)\b[^.?!]{0,40}\b(en|por|de) (slack|jira)\b")  # el contenido vive en otra herramienta y hay intención de leerla (no «mándalo por Slack»)
ADJUNTO = re.compile(r"\[image #|\bartifact\b|\bcapturas?\b|\badjunto\b|\bpantallazo")  # el contenido vive en una imagen o archivo adjunto
DEBIL = re.compile(r"\b(recuerdas|recuerdo|te acuerdas|me acuerdo|acuerdas)\b")  # «recuerdas…» solo no basta para descartar la carpeta
FUERTE2 = re.compile(r"\b(que|cual|en que|de que) (conversacion|sesion|chat)\b|\bconversacion (donde|en la que|que)\b")  # pedir «qué conversación fue» es una señal clara de lo hablado
COMANDO = re.compile(r"^\s*((alias|export|brew|npm|npx|pip3?|pipx|docker|ssh|scp|curl|wget|sudo|chmod|kubectl|gcloud)\s+\S|git\s+(status|push|pull|clone|commit|add|checkout|branch|merge|rebase|log|diff|stash|fetch|remote|init|reset)\b|(python3?(\.\d+)?|node|cd|ls|cat|echo|mkdir|rm|mv|cp|source|aws)\s+([-./~$'\"=@]|\S+\.\w{1,4}\b))")  # una línea de comando o configuración pegada (las palabras ambiguas —python, cat, cd…— solo si lo que sigue parece opción, ruta o archivo)
INSTALAR = re.compile(r"\b(instalar|instala|instalo|configurar|configura|configuro)\b.{0,50}\b(mac|macos|windows|linux|ubuntu|brew|homebrew|pip|npm)\b|\binstalar\b.{0,50}\bpaso a paso\b|\bpaso a paso\b.{0,40}\binstal")  # instalaciones generales: se resuelven en la web
PROPIOS = tuple(x for x in ("linear.app", "atlassian.net", *os.environ.get("BUSCADOR_DOMINIOS_PROPIOS", "").replace(" ", "").split(",")) if x)  # enlaces de la casa; los demás son externos
SIG_URL = "enlace externo: ábrelo y léelo primero; con su tema, busca"
EN_CURSO = re.compile(r"\b(como|que|cual) (quedo|quedaron|va(?! a\b)|van|vamos|falta|faltan|avanzo|avanzamos|hicimos|armamos|dejamos)\b|\ben que (quedo|quedamos|va|vamos|estamos)\b|\bque paso con\b|\blo que hemos (visto|hecho|armado|avanzado)\b|\bcomo (sigue|siguen)\b|\ben cola\b|\bestamos (haciendo|armando|trabajando)\b")  # «dime cómo quedó…», «cómo va…», «qué falta…»: proyectos en curso o en cola; son del trabajo del proyecto, no preguntas genéricas
AVANCE = re.compile(r"^\W*((listo|ok|okey|vale|si|dale|adelante|bien|perfecto|y|ahora|espera)\W+){0,3}que sigue\b")  # «¿qué sigue?»: pide que se continúe o la respuesta del tema de ese momento, dentro de la sesión
SIG_EXTERNO = "antes de buscar: lee primero la fuente externa (Slack/Jira) o el adjunto; con lo que salga, busca con esos términos"
SIG_WEB = "no hay nada propio que buscar: es una pregunta general, se resuelve con una búsqueda en la web"

ADJ_RUTA = re.compile(r"""@?["']?((?:/|~/)[^\n"'<>]*?\.(?:pdf|docx?|xlsx?|csv|pptx?|txt|md|json|png|jpe?g|heic|gif|zip))["']?""", re.I)
NOMBRE_GENERICO = re.compile(r"^(captura de pantalla|screenshot|screen shot|captura|image|img|imagen|foto|photo|scan|detail|result|resultado|resultados|export|exportacion|download|documento|document|untitled|sin titulo|copia de|count|select|query|consulta|output|salida|data|datos|file|archivo|tabla|table)(?![A-Za-zÁÉÍÓÚáéíóúñÑ])", re.I)


def adjuntos(msg):
    """Archivos adjuntos por ruta absoluta (@"…", '…' o suelta): [(nombre significativo o None, ruta)]. Un nombre sirve si trae al menos 2 palabras y no es genérico («Captura de pantalla…», «Detail_123.xlsx»)."""
    out = []
    for m in ADJ_RUTA.finditer(msg):
        ruta = m.group(1); base = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", ruta.rsplit("/", 1)[-1].strip())
        base = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])|(?<=[A-ZÁÉÍÓÚÑ])(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])", " ", base); palabras = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]+", base)  # el nombre completo, sin fechas ni números
        out.append((" ".join(palabras) if sum(len(w) >= 3 for w in palabras) >= 2 and not NOMBRE_GENERICO.match(base.strip()) else None, ruta))
    return out


def cargar_temas():
    """Temas propios del usuario (.context/enrutador-temas.tsv: raíz<TAB>fuente<TAB>nota) → fuente que conviene. Opcional: sin archivo no hay temas."""
    ruta = os.environ.get("BUSCADOR_TEMAS") or str(Path(__file__).resolve().parents[2] / ".context" / "enrutador-temas.tsv"); out = []
    try:
        for l in open(ruta, encoding="utf-8"):
            c = l.rstrip("\n").split("\t")
            if l.startswith("#") or len(c) < 2: continue
            k, f = norm(c[0].strip()), c[1].strip().lower()
            if k and f in ("conv", "carp", "ambas", "ninguna"): out.append((re.compile(r"\b" + re.escape(k)), f, c[0].strip()))
    except OSError: pass
    return out


TEMAS = cargar_temas()


def referencias(msg):
    out = {k: re.findall(p, msg) for k, p in REFS.items()}
    out["id"] = [x for x in out["id"] if x.split("-")[0].upper() not in NO_ID]
    extra = os.environ.get("BUSCADOR_ID_PATRON")
    if extra: out["id"] += re.findall(extra, msg)
    return {k: v for k, v in out.items() if v}


def ticket_pegado(msg, refs):
    """Ticket (o texto largo) pegado con un ID: su cuerpo trae verbos de pasado y «urgente» que NO son del pedido de hoy."""
    return "id" in refs and (msg.count("\n") >= 2 or len(msg) > 160)


def consulta_corta(msg, refs):
    """Para un ticket o texto pegado se busca por el ID y el título, no por todo el texto. El título es la línea con contenido real: la que trae el ID (sin el ID) o, si no, la de más palabras específicas; sin saludos, horas, nombres de chat, URL de ticket ni la instrucción del usuario."""
    ids = list(dict.fromkeys(refs.get("id", [])))[:3]; mejores = []; con_id = None
    for l in msg.splitlines():
        if not l.strip(): continue
        c = re.sub(r"</?pasted_content[^>]*>", " ", l); c = re.sub(r"\[\d{1,2}:\d{2}\]", " ", c)
        c = re.sub(r"https?://\S+", lambda m: " ".join(x for x in re.split(r"[-_/?=&.]+", m.group(0).rstrip("/").split("/")[-1]) if not (x.isdigit() or x.lower() in ("created", "true", "issue", "browse", "portal", "servicedesk", "customer"))), c)
        tiene_id = any(i in l for i in ids); c = " ".join(w for w in c.split() if w not in ids)
        c = limpiar_consulta(c) if FRASE_INSTR.match(norm(c)) or all(norm(w.strip(".,;:¿?¡!")) in INSTR | CONECTORES for w in c.split()) else c
        cw = palabras_contenido(c)
        if len(cw) < 2: continue
        if tiene_id and con_id is None: con_id = c
        mejores.append((especificos("x " + c) * 2 + len(cw), c))
    titulo = (con_id or (max(mejores)[1] if mejores else ""))[:100]
    return " ".join(ids + [titulo]).strip()


def urgente_en_pedido(msg, ids):
    """En un ticket pegado, la urgencia solo cuenta en líneas cortas sin ID (la instrucción del usuario), no en el cuerpo del ticket."""
    for l in msg.splitlines():
        if len(l) <= 60 and not any(i in l for i in ids) and (URGENTE_YA.search(l) or URGENTE.search(norm(l))): return True
    return False


def decidir(msg):
    msg = re.sub(r"\[Image: source:[^\]]*\]", "[Image #0]", msg)  # el marcador del sistema trae una ruta interna (su ruta interna parecía un ID de ticket)
    if re.fullmatch(r"(\s*\[Image #\d+\]\s*)+", msg): return {"buscar": False, "fuente": None, "k": 0, "rutas": False, "urgente": False, "refs": [], "tokens_aprox": 0, "motivo": "solo una imagen: se lee primero", "siguiente": SIG_EXTERNO}
    n = norm(msg); refs = referencias(msg); pegado = ticket_pegado(msg, refs); pegado_txt = (not pegado) and (msg.count("\n") >= 2 or len(msg) > 400)
    urgente = urgente_en_pedido(msg, refs.get("id", [])) if (pegado or pegado_txt) else bool(URGENTE_YA.search(msg) or URGENTE.search(n))
    hablado, escrito, ubicar = bool(HABLADO.search(n)), bool(ESCRITO.search(n)), bool(UBICAR.search(n))
    morfo = bool(PASADO_MORFO.search(n)) and bool(INTERROGATIVA.search(n))  # pregunta en pasado aunque no traiga una señal explícita
    base = {"buscar": False, "fuente": None, "k": 0, "rutas": False, "urgente": urgente, "refs": list(refs), "tokens_aprox": 0}
    if (len(msg.strip()) < 12 and not refs) or SALUDO.match(n): return {**base, "motivo": "saludo o respuesta corta"}  # un ID suelto («ABC-123») sí se busca
    if AVANCE.search(n) and not refs and len(msg.strip()) <= 60: return {**base, "motivo": "seguimiento: «¿qué sigue?» continúa lo que se está haciendo en la sesión"}
    en_curso = bool(EN_CURSO.search(n))
    if GENERICO.match(n) and not refs and not hablado and not escrito and not en_curso: return {**base, "motivo": "pedido genérico sin nada del proyecto"}
    if len(msg.strip()) <= 32 and SEGUIMIENTO.search(n) and not (refs or hablado or escrito): return {**base, "motivo": "seguimiento corto dentro de la tarea en curso"}
    if pegado: return {**base, "buscar": True, "fuente": "ambas", "k": 2, "motivo": "ticket pegado: se busca por ID y título en las dos fuentes", "tokens_aprox": TOKENS["ambas2"], "consulta": consulta_corta(msg, refs)}
    if pegado_txt:
        q = consulta_corta(msg, {})
        if q: return {**base, "buscar": True, "fuente": "ambas", "k": 3, "motivo": "texto pegado sin ID: se busca por su contenido, no por todo el texto", "tokens_aprox": TOKENS["ambas3"], "consulta": q}
        return {**base, "motivo": "texto pegado sin contenido buscable", "siguiente": SIGUIENTE}
    adj = [] if pegado else adjuntos(msg)
    if adj:  # archivo adjunto por ruta: un documento (pdf, xlsx, docx, csv…) se LEE por su ruta y se busca por su nombre y tema (V1 solo indexa la carpeta del proyecto: no encuentra lo de Descargas); una imagen sin nombre útil se lee primero
        resto = limpiar_consulta(ADJ_RUTA.sub(" ", msg)); nombres = [a for a, _ in adj if a]; docs = [r for _, r in adj if r.rsplit(".", 1)[-1].lower() not in ("png", "jpg", "jpeg", "heic", "gif")]
        q = " ".join(nombres + ([resto] if resto else []))[:160].strip()
        if docs and not nombres and len(palabras_contenido(resto)) < 3: q = (" ".join(re.sub(r"[_\-.]+", " ", r.rsplit("/", 1)[-1].rsplit(".", 1)[0]) for r in docs)[:120] + " " + resto).strip()  # nombre genérico y pedido corto: igual se busca por el nombre del archivo
        if nombres or docs or len(palabras_contenido(resto)) >= 3: return {**base, "buscar": True, "fuente": "ambas", "k": 2, "motivo": "archivo adjunto: se lee por su ruta y se busca por su nombre y tema", "tokens_aprox": TOKENS["ambas2"], "consulta": q}
        return {**base, "motivo": "imagen sin nombre útil (captura o nombre genérico): se lee primero", "siguiente": SIG_EXTERNO}
    if COMANDO.match(msg) and "?" not in msg and not (hablado or escrito): return {**base, "motivo": "comando o configuración pegado (nada que buscar)", "siguiente": SIG_WEB}
    if INSTALAR.search(n) and not escrito and not hablado: return {**base, "motivo": "instalación o configuración general (búsqueda en la web)", "siguiente": SIG_WEB}
    urls = re.findall(r"https?://\S+", msg)
    if urls and set(refs) <= {"url"} and not any(d in u for u in urls for d in PROPIOS) and len(palabras_contenido(limpiar_consulta(msg))) < 3: return {**base, "motivo": "enlace externo sin más contexto: se abre primero", "siguiente": SIG_URL}
    if en_curso and not refs and not escrito and not hablado: return {**base, "buscar": True, "fuente": "ambas", "k": 3, "motivo": "estado de algo en curso o en cola: se busca en las dos", "tokens_aprox": TOKENS["ambas3"]}
    if HOWTO.match(n) and not refs and not escrito and not hablado: return {**base, "motivo": "pregunta general de cómo-hacer (búsqueda en la web)", "siguiente": SIG_WEB}
    if TEMAS and not refs:
        fs = {f for rx, f, k in TEMAS if rx.search(n)}; ks = [k for rx, f, k in TEMAS if rx.search(n)]
        if fs:
            f = next(iter(fs)) if len(fs) == 1 else "ambas"
            if f == "ninguna": return {**base, "motivo": f"tema propio «{ks[0]}»: búsqueda en la web", "siguiente": SIG_WEB}
            fu = {"conv": "conversaciones", "carp": "carpeta", "ambas": "ambas"}[f]; tt = TOKENS["conversaciones"] if f == "conv" else (TOKENS["carpeta"] if f == "carp" else TOKENS["ambas3"])
            return {**base, "buscar": True, "fuente": fu, "k": 3, "motivo": f"tema propio «{ks[0]}» → {fu} (enrutador-temas.tsv)", "tokens_aprox": tt}
    cl = limpiar_consulta(msg); cw = palabras_contenido(cl)
    if not refs and EXTERNO.search(n): return {**base, "motivo": "depende de una fuente externa (Slack/Jira): se lee primero", "siguiente": SIG_EXTERNO}
    if not refs and ADJUNTO.search(n) and (not (hablado or morfo) or len(cw) < 4): return {**base, "motivo": "depende de un adjunto o imagen que no está en el texto", "siguiente": SIG_EXTERNO}
    if REFPREVIA.search(n) and len(cw) >= 2 and not refs: hablado = True; fuente_previa = True
    else: fuente_previa = False
    pregunta = bool(INTERROGATIVA.search(n)) and len(cw) >= 2  # una pregunta concreta de 2 palabras («¿qué proyectos son de X?») sí se busca
    if not refs and not hablado and not escrito and not morfo and not pregunta and len(cw) < 3 and especificos(cl) < 2:
        return {**base, "motivo": "sin contenido: solo una instrucción" if not cw else "pedido vago (menos de 3 palabras de contenido)", "siguiente": SIGUIENTE}
    exacto = any(k in refs for k in EXACTO); k = 2 if exacto else 3
    if hablado and escrito: fuente, motivo = "ambas", "señales de lo hablado y de lo escrito"
    elif hablado and not (morfo or FUERTE2.search(n) or (HABLADO.search(DEBIL.sub(" ", n)) and not fuente_previa)): fuente, motivo = "ambas", "referencia débil al pasado («recuerdas…», «lo de…»): se busca en las dos"
    elif hablado: fuente, motivo = "conversaciones", "pregunta por lo hablado (verbo de pasado, fecha o «¿qué decidimos?»)"
    elif morfo and not escrito: fuente, motivo = "conversaciones", "pregunta en pasado sobre algo que ocurrió"
    elif escrito: fuente, motivo = "carpeta", "pide ubicar o leer algo escrito"
    elif refs: fuente, motivo = "ambas", "inicio de tarea con " + "/".join(refs)
    else: fuente, motivo = "ambas", "tarea o pedido sin señal clara: se busca en las dos"
    rutas = fuente == "carpeta" and ubicar
    t = TOKENS["rutas"] if rutas else (TOKENS["carpeta"] if fuente == "carpeta" else (TOKENS["conversaciones"] if fuente == "conversaciones" else TOKENS[f"ambas{k}"]))
    out = {**base, "buscar": True, "fuente": fuente, "k": 5 if rutas else k, "rutas": rutas, "motivo": motivo, "tokens_aprox": t}
    if refs.get("id") and "url" in refs: out["consulta"] = consulta_corta(msg, refs)  # URL de ticket: ID + nombre de la URL
    elif cl and cl != msg.strip(): out["consulta"] = cl  # la instrucción («apóyame con…») no entra a la consulta
    return out
