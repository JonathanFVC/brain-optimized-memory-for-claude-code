"""ENRUTADOR DE BÚSQUEDA (2026-11-26): implementa el criterio de docs/criterio-busqueda.md con señales OBSERVABLES del pedido; solo biblioteca estándar, sin modelos, sin red.
decidir(mensaje) → {buscar, fuente: carpeta|conversaciones|ambas, k, rutas, urgente, motivo, tokens_aprox}.
Reglas (en este orden): 1) saludos y respuestas cortas, seguimientos cortos de la tarea en curso («súbelo»), y pedidos GENÉRICOS sin nada del proyecto → no se busca; 2) urgencia («YA», «apúrate», «urgente»…) → modo ligero solo para esa búsqueda;
3) señales de LO HABLADO (verbos de pasado con el usuario, fechas, «¿qué decidimos?», o una pregunta en pasado en general) → conversaciones; señales de LO ESCRITO («¿dónde está…?», «¿qué doc…?», «¿en qué archivo…?») → carpeta (solo rutas si basta ubicar el archivo); ambas señales o ninguna → las dos;
4) tamaño: 2 resultados si lo buscado es exacto (ID, archivo, error literal, texto entre comillas); si no, 3. Costos medidos (tokens de salida): ambas k3 ≈ 1,040 · ambas k2 ≈ 730 · conversaciones ≈ 580 · carpeta ≈ 490 · rutas ≈ 330.
Patrones genéricos; BUSCADOR_ID_PATRON agrega el de tus tickets. Las listas están a propósito al inicio del archivo para ajustarlas a otro idioma o equipo."""
import os, re, unicodedata

TOKENS = {"ambas3": 1040, "ambas2": 730, "conversaciones": 580, "carpeta": 490, "rutas": 330, "nada": 0}


def norm(s): return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


SALUDO = re.compile(r"^\s*((hola|buenas|gracias|muchas gracias|ok|okey|vale|listo|perfecto|si|no|adelante|dale|bien|ya|claro|entendido|buenisimo|genial|excelente|super|nada mas)\b[\s.!¡?¿,]*)+$")
HABLADO = re.compile(r"\b(dijimos|dijiste|dije|decidimos|decidiste|decidi|hablamos|hablaste|comentamos|quedamos|acordamos|acordaste|pedi|pediste|te pedi|te mande|me mandaste|mandamos|corrimos|ejecutamos|ejecute|hicimos|hiciste|hice|armamos|armaste|arme|propusiste|propuse|revisamos|vimos|mencionaste|mencione|explicaste|respondiste|contestaste|aplicamos|aplicaste|cambiamos|cambiaste|corregimos|resolvimos|recuerdas|te acuerdas|me acuerdo|no me acuerdo|la vez pasada|otra vez|como antes|retomemos|retomar|seguimos con)\b|\bque (se )?(decidio|dijo|paso|quedo|hicimos|corrimos|acordamos)\b|\bpor que (quedo|lo hicimos|elegimos|decidimos)\b|\b(ayer|anteayer|antier|semana pasada|mes pasado|hace \d+ (dias|semanas|meses)|el \d{1,2} de [a-z]+)\b|\bque (query|consulta|comando|sql) (corrimos|ejecutamos|usamos|hicimos)\b")
ESCRITO = re.compile(r"\b(donde (esta|queda|vive|se (guarda|documento|anoto))|en que (archivo|doc|documento|carpeta|ruta|script|modulo)|que (doc|documento|archivo|directiva|memoria|nota|script) |cual es (el|la) (doc|documento|archivo|ruta|directiva|script)|como (esta|quedo) documentad[oa]|esta documentad[oa]|hay (un )?(doc|documento|trazabilidad)|ya hay (un )?(doc|documento|trazabilidad)|ruta de|trazabilidad|directiva)\b")
PASADO_MORFO = re.compile(r"\b\w{3,}(amos|imos|aste|iste|aba|abamos|abas|aban|iamos|ian)\b|\b(habia|tenia|decia|sabia|queria|podia|hacia|veia|iba|era|eran|fue|fueron|quedo|quedaron|paso|salio|dio|dijo|pidio|llego|sumaba|faltaba|correspondia)\b")  # pasado en general (nosotros, tú, imperfecto y algunos irregulares)
INTERROGATIVA = re.compile(r"^\s*¿|\?\s*$|(^|[,;:]\s*)¿?(que|cual|cuales|cuanto|cuantos|cuantas|quien|quienes|cuando|donde|como|por que|a que|en que|para que|con que|de que|a quien|a cuantos)\b")
UBICAR = re.compile(r"\b(en que (archivo|script|modulo)|que archivo|donde esta (el|la) (archivo|script|funcion|clase|modulo)|cual es la ruta|ruta de)\b")
GENERICO = re.compile(r"^\s*(ayudame a|dime (como|que|cual)|que buenas practicas|recomiendame|sugiereme|explica(me)?|como funciona|que (es|son|significa|diferencia hay)|dame (un )?(ejemplo|ideas)|escribe (una|un) (funcion|script|regex|expresion|correo|texto)|traduce|resume|convierte|cuanto es|como (puedo|hago|calculo|configuro|medir|se hace)|genera (una|un) (tabla|lista|plan)|arma (un|una) plan de estudio|optimiza (esta|este)|revisa este codigo)\b")
SEGUIMIENTO = re.compile(r"\b\w+(elo|ela|elos|elas|alo|ala|alos|alas|ilo|ila|ilos|ilas|olo|ola|ulo|ula|melo|telo|selo)\b")  # verbo + pronombre («súbelo», «revísalo», «aplícalo»): seguimiento de la tarea en curso
URGENTE_YA = re.compile(r"\bYA\b")  # «YA» en mayúsculas (sobre el texto original)
URGENTE = re.compile(r"\b(apurate|apurense|urgente|urgentemente|rapido|rapidito|de inmediato|lo necesito ya|ahorita mismo|cuanto antes)\b")  # sobre el texto sin acentos
REFS = {"id": r"\b[A-Za-z]{2,6}-\d{2,6}\b", "url": r"https?://[^\s)>\]]+", "ruta": r"(?:[\w.\-]+/)+[\w.\-]+\.\w{1,5}\b", "archivo": r"\b[\w\-]+\.(?:py|sql|md|csv|tsv|xlsx|docx|pptx|json|sh|yml|yaml|txt)\b",
        "cita": r"[«\"“`]([^»\"”`\n]{3,60})[»\"”`]", "error": r"\b\w+(?:Error|Exception)\b"}
NO_ID = {"SHA", "MD", "ISO", "RFC", "AES", "RSA", "UTF", "TLS", "SSL", "IPV", "GPT", "WPA", "USB", "PDF"}  # prefijos con guion y número que NO son tickets («SHA-256», «ISO-8601»)
EXACTO = ("id", "archivo", "cita", "error")  # referencias exactas: bastan 2 resultados


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
    """Para un ticket pegado se busca por el ID y el título (primera línea, o el nombre en la URL), no por todo el texto."""
    ids = list(dict.fromkeys(refs.get("id", [])))[:3]
    primera = next((l.strip() for l in msg.splitlines() if l.strip()), "")
    primera = re.sub(r"https?://\S+", lambda m: re.sub(r"[-_]+", " ", m.group(0).rstrip("/").split("/")[-1]), primera)
    titulo = " ".join(w for w in primera.split() if w not in ids)[:100]
    return " ".join(ids + [titulo]).strip()


def urgente_en_pedido(msg, ids):
    """En un ticket pegado, la urgencia solo cuenta en líneas cortas sin ID (la instrucción del usuario), no en el cuerpo del ticket."""
    for l in msg.splitlines():
        if len(l) <= 60 and not any(i in l for i in ids) and (URGENTE_YA.search(l) or URGENTE.search(norm(l))): return True
    return False


def decidir(msg):
    n = norm(msg); refs = referencias(msg); pegado = ticket_pegado(msg, refs)
    urgente = urgente_en_pedido(msg, refs.get("id", [])) if pegado else bool(URGENTE_YA.search(msg) or URGENTE.search(n))
    hablado, escrito, ubicar = bool(HABLADO.search(n)), bool(ESCRITO.search(n)), bool(UBICAR.search(n))
    morfo = bool(PASADO_MORFO.search(n)) and bool(INTERROGATIVA.search(n))  # pregunta en pasado aunque no traiga una señal explícita
    base = {"buscar": False, "fuente": None, "k": 0, "rutas": False, "urgente": urgente, "refs": list(refs), "tokens_aprox": 0}
    if (len(msg.strip()) < 12 and not refs) or SALUDO.match(n): return {**base, "motivo": "saludo o respuesta corta"}  # un ID suelto («ABC-123») sí se busca
    if GENERICO.match(n) and not refs and not hablado and not escrito: return {**base, "motivo": "pedido genérico sin nada del proyecto"}
    if len(msg.strip()) <= 32 and SEGUIMIENTO.search(n) and not (refs or hablado or escrito): return {**base, "motivo": "seguimiento corto dentro de la tarea en curso"}
    if pegado: return {**base, "buscar": True, "fuente": "ambas", "k": 2, "motivo": "ticket pegado: se busca por ID y título en las dos fuentes", "tokens_aprox": TOKENS["ambas2"], "consulta": consulta_corta(msg, refs)}
    exacto = any(k in refs for k in EXACTO); k = 2 if exacto else 3
    if hablado and escrito: fuente, motivo = "ambas", "señales de lo hablado y de lo escrito"
    elif hablado: fuente, motivo = "conversaciones", "pregunta por lo hablado (verbo de pasado, fecha o «¿qué decidimos?»)"
    elif morfo and not escrito: fuente, motivo = "conversaciones", "pregunta en pasado sobre algo que ocurrió"
    elif escrito: fuente, motivo = "carpeta", "pide ubicar o leer algo escrito"
    elif refs: fuente, motivo = "ambas", "inicio de tarea con " + "/".join(refs)
    else: fuente, motivo = "ambas", "tarea o pedido sin señal clara: se busca en las dos"
    rutas = fuente == "carpeta" and ubicar
    t = TOKENS["rutas"] if rutas else (TOKENS["carpeta"] if fuente == "carpeta" else (TOKENS["conversaciones"] if fuente == "conversaciones" else TOKENS[f"ambas{k}"]))
    return {**base, "buscar": True, "fuente": fuente, "k": 5 if rutas else k, "rutas": rutas, "motivo": motivo, "tokens_aprox": t}
