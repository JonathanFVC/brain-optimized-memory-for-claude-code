# Criterio de búsqueda (general) · Search criterion (general) — versión refinada _(2026-11-26 18:53)_

> Criterio de búsqueda (V1 carpeta + V2 conversaciones), general y replicable: señales observables del mensaje → si buscar, en qué fuente y cuántos resultados. Se aplica con `scripts/buscador/buscar_todo.py --auto`; el registro de uso y el informe viven en `~/.memoria-local/uso/`. · General, replicable criterion: observable signals in the message → whether to search, which source and how many results.
> **Idea central:** la búsqueda es un primer paso barato (≈ 1,100 tokens, 5–9 s) que evita rehacer trabajo, preguntar lo que ya se dijo o afirmar «no hay» sin mirar. Para que de verdad se use, la regla de entrada no puede depender de un juicio ambiguo.

# ESPAÑOL

## 1. Regla de entrada (sin juicio): ¿es una tarea?
**Toda tarea nueva** lleva **una** búsqueda (en una o en las dos fuentes, según la sección 5) con `buscar_todo` **antes de analizar o construir**. Tarea = pedido de **hacer, revisar, analizar, corregir, consultar datos o retomar algo** sobre el proyecto (un ticket, un archivo, una tabla, un entregable, un error, un tema). Lo decide la forma del pedido, no mi impresión de si «hará falta».
Además, **aunque no sea una tarea**, se busca en estos tres casos: (a) el usuario pregunta por el pasado («¿qué decidimos?», «como la vez pasada», «¿qué corrimos para…?»); (b) **antes de decir «no hay», «no consta» o «no lo recuerdo»**; (c) antes de pedirle al usuario un dato que quizá ya dio.

## 2. Cuándo NO se busca (lista cerrada)
- Saludos, agradecimientos y respuestas cortas («gracias», «adelante», «sí»).
- Preguntas o pedidos **genéricos sin nada del proyecto** («explica qué es un índice», «escribe una función que sume dos listas»).
- Seguimientos **dentro de la misma tarea** cuyo tema ya se buscó (no se repite salvo que aparezca un término concreto nuevo).
- Cuando el usuario dice explícitamente que no se busque.
Si hay duda entre «tarea del proyecto» y «genérico», **se busca** (cuesta ≈ 1,100 tokens; fallar cuesta más).

## 3. Presupuesto (para no gastar de más)
Una búsqueda por tarea. Si el resultado es de **confianza baja**, se **reformula una sola vez** con otros términos; después se dice «no encontré» y se sigue. Máximo 2 búsquedas por pedido. No se repite la misma consulta en la misma sesión.

## 4. Cómo formular la consulta
Términos distintivos, no el mensaje entero: el ID o enlace del ticket, el archivo o la ruta, la tabla, el proyecto, la persona, el texto exacto del error, y el tema en 2–4 palabras. Una fecha en español («ayer», «el 12 de enero») filtra por día. Si el pedido no trae nada concreto, se usan sus 3–5 palabras más específicas.

## 5. Qué fuente, qué modo y cuántos resultados (lo decide quien busca, con estas señales)
**Costo medido de una búsqueda** (tokens de salida): ambas fuentes con 3 resultados ≈ 1,040 · ambas con 2 ≈ 730 · solo conversaciones ≈ 580 · solo carpeta ≈ 490 · solo rutas (V1 rápida, 5 resultados) ≈ 330. El modo urgente no ahorra tokens (≈ 1,070): ahorra tiempo (≈ 5 s en vez de ≈ 9 s).

| Señal observable en el pedido | Fuente | Tamaño |
|---|---|---|
| Pide **ubicar o leer algo escrito**: «¿dónde está…?», «¿qué doc…?», nombra una ruta, archivo, directiva o memoria, «¿cómo está documentado…?» | 📁 **solo carpeta** (V1) | 3 resultados; si solo hay que ubicar el archivo, V1 rápida con `--rutas` (≈ 330 tokens) |
| Pregunta por **lo hablado**: verbos de pasado con el usuario («dijimos», «decidimos», «pedí», «corrimos», «te mandé»), «¿por qué quedó así?», una fecha («ayer»), un query o comando que se corrió | 💬 **solo conversaciones** (V2) | 3 resultados |
| **Inicio de tarea** con ticket, ID, proyecto, tema o error (puede estar en cualquiera de las dos) | 📁💬 **ambas** (`buscar_todo`) | 2 resultados si el término es exacto (ID, archivo, error literal); si no, 3 |
| Antes de decir «no hay» o «no consta» | la fuente donde se esperaba; si no está claro, ambas | 3 resultados |
| Sin señal clara | 📁💬 **ambas** | 3 resultados |
**Modo:** el base (V1 Profunda, V2 Máxima); con urgencia («YA», «apúrate»), ligero y solo para esa búsqueda; una bandera explícita manda.
**Escalada:** resultado de confianza baja → una reformulación; si persiste y se buscó una sola fuente, se añade la otra; no más.
**Regla de ahorro:** una sola fuente cuando la señal es clara (≈ −50 % de tokens), ambas solo cuando no lo es; 2 resultados en vez de 3 cuando lo buscado es exacto (≈ −30 %); solo rutas cuando basta con ubicar el archivo (≈ −68 %).

## 5 bis. Criterios funcionales implementados (enrutador `enrutar_busqueda.py`) _(2026-11-26 19:05)_
El enrutador aplica estas señales **en este orden**; la primera que cae decide. Solo texto: sin modelos ni red (≈ 0 ms). Se prueba con `buscar_todo.py "<mensaje>" --explica` (muestra la decisión sin buscar) o `--auto` (decide y busca).
| # | Señal observable en el mensaje | Decisión |
|---|---|---|
| 1 | Saludo, agradecimiento o respuesta corta (< 12 caracteres, o «gracias, listo», «adelante»…) **sin** ID de ticket | **No se busca** |
| 2 | Pedido genérico sin nada del proyecto («explica…», «cómo funciona…», «qué es…», «dame un ejemplo…», «recomiéndame…») y sin ID, verbo de pasado ni «dónde está» | **No se busca** |
| 3 | Seguimiento corto de la tarea en curso (≤ 32 caracteres, verbo + pronombre: «súbelo», «revísalo») sin referencias | **No se busca** |
| 4 | Verbo de pasado con el usuario («dijimos», «decidimos», «corrimos», «te pedí»…), fecha, «¿qué decidimos?» **y también** señal de lo escrito | **Ambas fuentes** |
| 5 | Solo lo hablado (los verbos/fechas de arriba), o una **pregunta en pasado** sin señal de lo escrito | **Solo conversaciones** (V2 Máxima) |
| 6 | Solo lo escrito («¿dónde está…?», «¿en qué archivo…?», «¿qué doc…?»); si pide ubicar un archivo/script/ruta → modo `--rutas` (k = 5, ≈ 330 tokens) | **Solo carpeta** (V1 Profunda) |
| 7 | ID, URL, ruta, archivo, cita entre comillas o error sin otra señal; o tarea sin señal clara | **Ambas fuentes** |
| — | **Tamaño:** 2 resultados si hay referencia exacta (ID, archivo, cita, error); si no, 3. Con `--rutas`, 5 | |
| — | **Urgencia:** «YA» en mayúsculas, «apúrate», «urgente», «rápido», «de inmediato», «cuanto antes»… → `--urgente` (modo ligero; ahorra tiempo ≈ 5 s vs ≈ 9 s, no tokens) | |
Costos medidos (tokens de salida): ambas k3 ≈ 1,040 · ambas k2 ≈ 730 · conversaciones ≈ 580 · carpeta ≈ 490 · rutas ≈ 330 · nada 0.
**Adaptación a otro equipo:** las listas de verbos y patrones están al inicio del archivo; `BUSCADOR_ID_PATRON` agrega el formato de tus tickets.
**Resultados de la prueba (288 mensajes; `tests/test_enrutador.py`):** conversaciones 92 afinadas 98 % · 91 de control (no vistas al afinar) 96 % · carpeta (51) 98 % · genéricos 100 % · seguimientos 100 % · tareas 100 % · urgentes 10/10 con 0 falsos urgentes en 278 · casos de oro 12/12. Ahorro frente a «buscar siempre en las dos con 3» (≈ 1,040): ≈ 770 tokens por mensaje en promedio (−26 %); −19/−21 % en preguntas de conversación, −5 % en carpeta, −10 % en tareas, −98 % en genéricos y seguimientos.
**Límites honestos:** (a) la prueba se afinó con 92 de los mensajes (el control de 91 baja 2 puntos); (b) el ahorro en tareas y carpeta es pequeño porque ahí casi siempre se busca en las dos fuentes; (c) las preguntas de conversación sin verbo de pasado ni fecha caen a «ambas» (cuesta más, no falla); (d) los fallos restantes son preguntas ambiguas donde el criterio manda a buscar en las dos.

**Ticket pegado** _(2026-11-26 19:08)_: si el mensaje trae un ID y es largo (≥ 3 líneas o > 160 caracteres), se busca **siempre en las dos fuentes con 2 resultados**, por **ID + título** (no por todo el texto), y se ignoran los verbos de pasado y «urgente» del cuerpo del ticket; la urgencia solo cuenta en líneas cortas sin ID (la instrucción de hoy: «hazlo YA»).

**IDs que no son tickets** _(2026-11-26)_: prefijos con guion y número como `SHA-256`, `ISO-8601`, `RFC-2616` no cuentan como ID de ticket (lista `NO_ID` en `enrutar_busqueda.py`); `BUSCADOR_ID_PATRON` agrega el formato de tus tickets.

## 6. Qué se hace con el resultado
- Es un **mapa**, no la respuesta: se abre el rango citado (`ruta:línea` o `sesión:línea`), se mira la **fecha** (puede haber decisiones superadas) y se **verifica el estado vivo** antes de afirmar algo.
- La confianza «baja» no se cita como hecho; «media» y «alta» se verifican igual.
- Se marca `--util N` o `--inutil N` (registro local de uso) sin pedirle nada al usuario.
- Si el resultado cambia el plan o ahorra trabajo, se dice en una línea.

## 7. Evidencia visible
La **primera respuesta de cada tarea** lleva una línea: «🔎 Búsqueda: 2 coincidencias útiles en la carpeta, 1 en conversaciones (sesión:línea) / ninguna». Así se ve que se usó y se puede medir con `--uso-stats`.

## 8. Si algo falla
Modelos no instalados o error: se avisa en una línea y se usa el modo disponible más cercano (nunca se calla); índice vacío: se dice y se sigue con la documentación. Nunca se inventa un resultado.

## 9. Privacidad
El índice guarda **todo sin enmascarar**. Los resultados pueden traer contraseñas o datos de personas: se usan solo para el trabajo del usuario, **nunca se pegan en lugares compartidos o públicos** sin permiso, y `--ocultar` los enmascara al mostrarlos.

## 11. Cómo se revisa
A las dos semanas, con `--uso-stats`: consultas por tarea, fracción marcada y fracción útil. Si menos del 40 % de las búsquedas resultan útiles, se aprieta la lista de «cuándo NO»; si casi nunca se usa, se revisa que la regla de entrada se esté aplicando.

## Casos de prueba del criterio (para comprobar que no es ambiguo)
| Mensaje | ¿Busca? | Fuente |
|---|---|---|
| «Revisa el ticket ABC-123 y dime qué falta» | Sí (tarea) | Las dos, 2 resultados (ID exacto) |
| «¿Qué decidimos del formato del reporte?» | Sí (pasado) | V2 (o las dos) |
| «Actualiza scripts/etl/carga.py para que filtre por fecha» | Sí (tarea con archivo) | Las dos |
| «Arma el entregable que hicimos el mes pasado, pero con datos nuevos» | Sí (tarea + pasado) | Las dos |
| «¿Dónde está el doc de la migración?» | Sí | Solo V1 |
| «¿Qué decidimos ayer del formato del reporte?» | Sí | Solo V2 |
| «¿En qué archivo está la función de carga?» | Sí | Solo V1, `--rutas` |
| «Explica qué es un índice en una base de datos» | No (genérico) | — |
| «Gracias, listo» | No | — |
| «Ahora súbelo» (seguimiento de la misma tarea ya buscada) | No | — |
| «YA, necesito el query de la carga mensual» | Sí, ligero | Las dos, `--urgente` |
| «No me acuerdo si ya lo hicimos…» | Sí (antes de decir «no hay») | Las dos |
| «Escribe una función que ordene una lista» | No (genérico) | — |
| «Corrige este error: KeyError en el módulo de pagos» | Sí (tarea con error y módulo) | Las dos |

# ENGLISH

## 1. Entry rule (no judgment): is it a task?
**Every new task** gets **one** `buscar_todo` search (in one or both sources, per section 5) **before analyzing or building**. Task = a request to **do, review, analyze, fix, query data or pick up something** about the project (a ticket, a file, a table, a deliverable, an error, a topic). The shape of the request decides, not my impression of whether it will "be needed".
Also, **even when it is not a task**, search in three cases: (a) the user asks about the past ("what did we decide?", "like last time", "what did we run for…?"); (b) **before saying "there is nothing", "not recorded" or "I don't remember"**; (c) before asking the user for something they may have already given.

## 2. When NOT to search (closed list)
- Greetings, thanks and short replies ("thanks", "go ahead", "yes").
- **Generic** questions or requests with **nothing from the project** ("explain what an index is", "write a function that adds two lists").
- Follow-ups **inside the same task** whose topic was already searched (not repeated unless a new concrete term appears).
- When the user explicitly says not to search.
If it is unclear whether it is a "project task" or "generic", **search** (≈ 1,100 tokens; missing costs more).

## 3. Budget
One search per task. If the result has **low confidence**, **reformulate once** with different terms; then say "nothing found" and move on. At most 2 searches per request. Never repeat the same query in a session.

## 4. How to phrase the query
Distinctive terms, not the whole message: the ticket ID or link, the file or path, the table, the project, the person, the exact error text, and the topic in 2–4 words. A date in Spanish ("ayer", "el 12 de enero") filters by day. If the request has nothing concrete, use its 3–5 most specific words.

## 5. Which source, which mode and how many results (decided by whoever searches, using these signals)
**Measured cost of one search** (output tokens): both sources with 3 results ≈ 1,040 · both with 2 ≈ 730 · conversations only ≈ 580 · folder only ≈ 490 · paths only (V1 fast, 5 results) ≈ 330. Urgent mode does not save tokens (≈ 1,070): it saves time (≈ 5 s instead of ≈ 9 s).

| Observable signal in the request | Source | Size |
|---|---|---|
| Asks to **locate or read something written**: "where is…?", "which doc…?", names a path, file, directive or memory, "how is it documented…?" | 📁 **folder only** (V1) | 3 results; if only the file must be located, V1 fast with `--rutas` (≈ 330 tokens) |
| Asks about **what was said**: past-tense verbs with the user ("we said", "we decided", "I asked", "we ran", "I sent you"), "why did it end that way?", a date ("yesterday"), a query or command that was run | 💬 **conversations only** (V2) | 3 results |
| **Start of a task** with a ticket, ID, project, topic or error (could be in either source) | 📁💬 **both** (`buscar_todo`) | 2 results if the term is exact (ID, file, literal error); otherwise 3 |
| Before saying "there is nothing" or "not recorded" | the source where it was expected; if unclear, both | 3 results |
| No clear signal | 📁💬 **both** | 3 results |
**Mode:** the base one (V1 Deep, V2 Max); on urgency ("NOW", "hurry"), light and only for that search; an explicit flag wins.
**Escalation:** low-confidence result → one reformulation; if it persists and only one source was searched, add the other; no more.
**Saving rule:** one source when the signal is clear (≈ −50 % tokens), both only when it is not; 2 results instead of 3 when what is sought is exact (≈ −30 %); paths only when locating the file is enough (≈ −68 %).

## 5 bis. Functional criteria implemented (router `enrutar_busqueda.py`) _(2026-11-26 19:05)_
Signals are applied **in this order**; the first match decides. Text-only: no models, no network (≈ 0 ms). Try `buscar_todo.py "<message>" --explica` (shows the decision without searching) or `--auto` (decides and searches).
1) greeting / thanks / short reply (<12 chars) without a ticket ID → **no search**; 2) generic request with nothing project-specific → **no search**; 3) short follow-up (≤32 chars, verb+pronoun) → **no search**; 4) past-tense verb with the user, date or "what did we decide?" **and** a written-thing signal → **both sources**; 5) spoken-only, or a past-tense question → **conversations only** (V2 Máximo); 6) written-only ("where is…", "which file…") → **folder only** (V1 Profundo), `--rutas` (k=5, ≈330 tokens) when asking to locate a file/script/path; 7) ID/URL/path/file/quote/error alone, or a task with no clear signal → **both**. Size: 2 results with an exact reference, else 3. Urgency ("YA" in caps, "hurry", "urgent", "ASAP"-type words) → `--urgente` (light mode; saves time, not tokens).
Measured output tokens: both k3 ≈1,040 · both k2 ≈730 · conversations ≈580 · folder ≈490 · paths ≈330 · none 0.
Results (288 messages): conversations 98 % tuned / 96 % held-out · folder 98 % · generic 100 % · follow-ups 100 % · tasks 100 % · urgent 10/10, 0 false urgents in 278 · gold cases 12/12. Average ≈770 tokens/message (−26 % vs always-both-k3); −5 % on folder and −10 % on tasks, −98 % on generic/follow-ups.
Honest limits: tuned on 92 of the messages (held-out 2 points lower); small savings on tasks/folder because both sources are almost always searched; conversation questions with no past-tense/date cue fall to "both" (costs more, doesn't fail).

**Pasted ticket** _(2026-11-26 19:08)_: an ID plus a long message (≥3 lines or >160 chars) → always both sources, 2 results, queried by **ID + title** (not the whole text); past-tense verbs and "urgent" inside the ticket body are ignored; urgency counts only on short lines without the ID (today's instruction).

**IDs that are not tickets** _(2026-11-26)_: hyphen-plus-number prefixes such as `SHA-256`, `ISO-8601`, `RFC-2616` do not count as ticket IDs (`NO_ID` list in `enrutar_busqueda.py`); `BUSCADOR_ID_PATRON` adds your own ticket format.

## 6. What to do with the result
- It is a **map**, not the answer: open the cited range (`path:line` or `session:line`), check the **date** (decisions may be superseded) and **verify the live state** before asserting anything.
- "Low" confidence is not quoted as fact; "medium" and "high" are verified anyway.
- Mark `--util N` or `--inutil N` (local usage log) without asking the user.
- If the result changes the plan or saves work, say so in one line.

## 7. Visible evidence
The **first reply of each task** carries one line: "🔎 Search: 2 useful matches in the folder, 1 in conversations (session:line) / none". It shows the search was used and can be measured with `--uso-stats`.

## 8. If something fails
Models not installed or an error: say so in one line and use the closest available mode (never stay silent); empty index: say so and continue with the documentation. Never invent a result.

## 9. Privacy
The index stores **everything unmasked**. Results may contain passwords or personal data: use them only for the user's work, **never paste them into shared or public places** without permission, and `--ocultar` masks them when displaying.

## 11. How it is reviewed
After two weeks, with `--uso-stats`: searches per task, fraction marked and fraction useful. If fewer than 40 % of searches turn out useful, tighten the "when NOT" list; if it is almost never used, check that the entry rule is being applied.
