---
name: buscar-conversaciones
description: Busca en las conversaciones pasadas de Claude Code (100 % local) cuando el usuario pregunta qué se dijo, decidió, corrió o devolvió antes, o antes de afirmar «no consta» o «no hay». Usa el modo base (Máximo por defecto) y --ligero solo si el usuario pide algo urgente.
---

# Buscar en conversaciones pasadas

Usa esta skill cuando la pregunta es sobre **lo hablado y no documentado** («¿qué dijimos de X?», «¿por qué quedó así?», «¿qué query corrimos?», «¿qué decidimos el 12 de enero?») o cuando vayas a responder «no consta» sin haber mirado las sesiones.

## Cómo
1. **Formula una consulta corta con términos distintivos** (nombres, archivos, comandos, tablas, personas y tema), no pegues el mensaje entero: con muchas palabras comunes el ranking se diluye. Una fecha en español («ayer», «la semana pasada», «el 12 de enero») filtra por día; «hoy» solo filtra si no hay otra fecha.
2. **Corre** `python3 -I scripts/buscador/buscar_sesiones.py "<consulta>" --excluir <uuid de la sesión actual> [-k 3]` (el uuid sale del nombre del `.jsonl` de la sesión actual). Si la consulta es específica, `-k 3` ahorra tokens.
3. **Elige el modo:**
   - **Modo base (sin bandera):** el que el usuario haya elegido (con `--modo`); por defecto **Máximo** si está instalado (≈ 7–12 s) y, si no, **Profundo** (≈ 5–9 s).
   - **`--ligero` (≈ 3–7 s):** **solo cuando el usuario pida algo urgente** («lo necesito YA», «apúrate», «urgente»): esa búsqueda sale ligera aunque el modo base sea otro. Si no encuentra nada o termina con «→ Sugerencia: confianza baja», dile al usuario que no encontraste nada y que sigues con una búsqueda profunda, y córrela sin `--ligero`.
   - **`--ultraligero` (o `--solo-v2`):** sin modelos (≈ 0.1 s) y de menor precisión; solo si el usuario lo elige.
4. **Lee el resultado como un mapa:** abre el rango citado (`uuid:línea` en el `.jsonl`), confirma, mira la fecha (puede haber decisiones superadas) y verifica el estado vivo.
5. **Marca el uso:** `--util N` si el fragmento sirvió, `--inutil N` si no (registro local; `--uso-stats` lo resume).

## Con la carpeta del proyecto y el enrutador (`buscar_todo.py`)
Para **tareas nuevas**, tickets pegados y preguntas que pueden estar en archivos o en conversaciones, usa en su lugar `python3 -I scripts/buscador/buscar_todo.py "<mensaje>" --auto --excluir <uuid actual>`: el enrutador decide si buscar, en qué fuente (V1 carpeta, V2 conversaciones o las dos) y cuántos resultados, según `docs/criterio-busqueda.md`. Al cerrar la tarea corre `buscar_todo.py --marca v1|v2|ambas|ninguna <tarea>` y deja en una línea «🔎 Búsqueda: <fuente> → aportó <marca>». `--explica` solo muestra la decisión.

## Límites
- Solo busca en las sesiones del proyecto actual (otra carpeta con `--sesiones`).
- El índice guarda todo sin enmascarar: es una copia sensible; `--ocultar` solo enmascara al mostrar.
- Si el modo con modelos no está instalado, avisa y usa V2: instala con `python3 -I scripts/buscador/preparar_profundo.py` (Ligero y Profundo) y, opcional, `preparar_maximo.py` (Máximo); son las únicas partes con red.
- Las preguntas con dos partes en turnos distintos («¿cómo se llamó X y cuándo hicimos Y?») fallan más: si no aparecen las dos, busca cada parte por separado.
- Si no aparece nada tras escalar una vez, no digas «no hay»: dilo con la confianza que tengas y revisa documentos y memoria.
