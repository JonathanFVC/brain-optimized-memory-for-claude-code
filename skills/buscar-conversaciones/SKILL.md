---
name: buscar-conversaciones
description: Busca en las conversaciones pasadas de Claude Code (100 % local) cuando el usuario pregunta qué se dijo, decidió, corrió o devolvió antes, o antes de afirmar «no consta» o «no hay». Usa ligero por defecto y --profundo cuando haga falta.
---

# Buscar en conversaciones pasadas

Usa esta skill cuando la pregunta es sobre **lo hablado y no documentado** («¿qué dijimos de X?», «¿por qué quedó así?», «¿qué query corrimos?», «¿qué decidimos el 12 de enero?») o cuando vayas a responder «no consta» sin haber mirado las sesiones.

## Cómo
1. **Formula una consulta corta con términos distintivos** (nombres, archivos, comandos, tablas, personas y tema), no pegues el mensaje entero: con muchas palabras comunes el ranking se diluye. Una fecha en español («ayer», «la semana pasada», «el 12 de enero») filtra por día; «hoy» solo filtra si no hay otra fecha.
2. **Corre** `python3 -I scripts/buscador/buscar_sesiones.py "<consulta>" --excluir <uuid de la sesión actual> [-k 3]` (el uuid sale del nombre del `.jsonl` de la sesión actual). Si la consulta es específica, `-k 3` ahorra tokens.
3. **Elige el modo:**
   - **Ligero (por defecto, ≈ 7 s):** lo concreto y recurrente.
   - **`--profundo` (≈ 9 s):** si el ligero termina con «→ Sugerencia: confianza baja», si la pregunta es vaga o parafraseada, si la respuesta servirá para actuar o afirmar algo importante, o antes de reformular a ciegas. Escala **una vez** en lugar de reformular varias.
   - **`--solo-v2`:** solo en emergencias (sin modelos, menor precisión).
4. **Lee el resultado como un mapa:** abre el rango citado (`uuid:línea` en el `.jsonl`), confirma, mira la fecha (puede haber decisiones superadas) y verifica el estado vivo.
5. **Marca el uso:** `--util N` si el fragmento sirvió, `--inutil N` si no (registro local; `--uso-stats` lo resume).

## Límites
- Solo busca en las sesiones del proyecto actual (otra carpeta con `--sesiones`).
- El índice guarda todo sin enmascarar: es una copia sensible; `--ocultar` solo enmascara al mostrar.
- Si el modo con modelos no está instalado, avisa y usa V2: instala con `python3 -I scripts/buscador/preparar_profundo.py` (única parte con red).
- Si no aparece nada tras escalar una vez, no digas «no hay»: dilo con la confianza que tengas y revisa documentos y memoria.
