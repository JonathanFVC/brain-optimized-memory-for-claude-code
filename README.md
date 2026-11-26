# brain-optimized-memory-for-claude-code

**🇲🇽 [ESPAÑOL](#español)** (primero, aquí abajo) · **🇬🇧 [ENGLISH](#english)** (below, same page)

---

# ESPAÑOL

## Memoria local para Claude Code

Búsqueda 100 % local en tus **conversaciones pasadas de Claude Code**, más un sistema de *directivas*, *memoria* y *skills* reutilizables que hace que Claude siga tus reglas con poco contexto. Nada sale de tu equipo mientras buscas; lo único que usa la red es instalar dos modelos abiertos, una sola vez.


## Qué incluye
- **`scripts/buscador/`**: búsqueda de conversaciones. **V2** (BM25 sobre palabras y prefijos de 5 letras + fusión RRF + fechas en español, SQLite FTS5, solo biblioteca estándar de Python) y dos modos con modelos: **ligero** (candidatos de V2 reordenados por `gte-multilingual-reranker-base`) y **profundo** (suma vectores de `multilingual-e5-small`). Ambos corren sin red, en un entorno aislado, con modelos de solo lectura y verificados por huella. **Al terminar la instalación el entorno queda sellado automáticamente: ni usando su Python directamente puede salir a internet** (compruébalo cuando quieras con `scripts/buscador/verificar_aislamiento.py`).
- **`scripts/directivas-buscador/`**: un hook que en cada mensaje inyecta solo las directivas y memorias más afines, para no cargar un archivo de reglas largo cada vez.
- **`.context/`, `plantillas/`**: directivas de ejemplo, palabras de disparo, `CLAUDE.md`, configuración de hooks y memorias (todo ficticio; reemplázalo por lo tuyo).
- **`skills/`**: tres skills reutilizables: `buscar-conversaciones`, `trazabilidad`, `actualizar-directivas`.
- **`docs/`**: arquitectura, directivas y memoria, seguridad y privacidad, resultados y lecciones.

## Inicio rápido
Requiere Python ≥ 3.12 (se recomienda macOS; la capa de sistema contra la red usa `sandbox-exec`).
```bash
# 1) opcional, una vez (con red): instalar el entorno aislado y los dos modelos; al terminar se sella solo contra internet
python3 -I scripts/buscador/preparar_profundo.py

# 2) buscar en las sesiones del proyecto actual (por defecto, modo ligero)
python3 -I scripts/buscador/buscar_sesiones.py "¿qué decidimos del formato del reporte semanal?" --excluir <uuid de la sesión actual>
python3 -I scripts/buscador/buscar_sesiones.py "pregunta vaga o parafraseada" --profundo
python3 -I scripts/buscador/buscar_sesiones.py "término exacto" --solo-v2     # sin modelos
```
Para usar las directivas y el hook en tu proyecto: copia `scripts/`, `.context/` y `plantillas/CLAUDE.md` (como `CLAUDE.md`), mezcla `plantillas/settings.json` en `.claude/settings.json`, copia `skills/*` a `.claude/skills/` y escribe tus directivas con el formato descrito al inicio de `.context/directivas.md`. Luego corre `python3 -I scripts/directivas-buscador/directivas_buscador.py mapa`.

Variables de entorno: `BUSCADOR_HOME` (dónde viven índice y modelos, por defecto `~/.memoria-local`), `CLAUDE_PROJECT_DIR`, `BUSCADOR_ZONA` (zona horaria), `BUSCADOR_SIGLAS` (siglas de 2 letras que cuentan como palabra).

## Números (historial del autor, 183 preguntas de prueba, parte escritas por Claude)
| Modo | Respuesta en el top 5 | Primer resultado | MRR | Comando completo |
|---|---|---|---|---|
| Solo V2 | 58 % | 38 % | 0.467 | ≈ 0.1 s |
| Ligero | 70 % | 54 % | ≈ 0.60 | ≈ 7 s |
| Profundo | 73 % | 56 % | ≈ 0.63 | ≈ 9 s |
Una persona, un historial: mide con tus propias preguntas (`scripts/buscador/evaluacion/evaluar_metodos.py`). Detalles y lo que no funcionó (un modelo propio pequeño) en `docs/resultados.md`.

## Privacidad
El índice guarda **todo lo que escribiste, sin enmascarar** (contraseñas incluidas si las pegaste). Mantén `~/.memoria-local` privado y no lo publiques. Los modelos son abiertos (MIT y Apache-2.0), con commit fijado, huella verificada y de solo lectura; las búsquedas corren con la red bloqueada en tres capas (archivos, código, sistema). Los límites se describen con honestidad en `docs/seguridad-y-privacidad.md`.

## Pruebas
`python3 -I tests/smoke_test.py` arma un proyecto y sesiones sintéticas en una carpeta temporal y comprueba el analizador de fechas, la búsqueda, el mapa de directivas y el hook. Nunca toca tu índice real.

## Licencia
MIT. Los modelos de terceros conservan sus licencias (MIT, Apache-2.0).

---

# ENGLISH

## Local memory for Claude Code

100 % local search over your **past Claude Code conversations**, plus a small system of reusable *directives*, *memory* and *skills* that keeps Claude following your rules with little context. Nothing leaves your machine while you search; the only step that uses the network is installing two open models once.


## What is inside
- **`scripts/buscador/`** – conversation search. **V2** (BM25 over words and 5-letter prefixes + RRF fusion + Spanish date filters, SQLite FTS5, Python standard library only) and two model-based modes: **light** (V2 candidates re-ranked by `gte-multilingual-reranker-base`) and **deep** (also adds `multilingual-e5-small` vectors). Both run offline in an isolated environment, with read-only, hash-verified models. **When the install finishes, the environment is sealed automatically: even running its Python directly cannot reach the internet** (verify any time with `scripts/buscador/verificar_aislamiento.py`).
- **`scripts/directivas-buscador/`** – a hook that, on every message, injects only the directives and memories most relevant to it, so a long rules file does not have to be loaded every time.
- **`.context/`, `plantillas/`** – example directives, trigger words, `CLAUDE.md`, hook settings and memory files (all fictional examples; replace them with yours).
- **`skills/`** – three reusable skills: `buscar-conversaciones`, `trazabilidad`, `actualizar-directivas`.
- **`docs/`** – architecture, directives and memory, security and privacy, results and lessons (Spanish).

## Quick start
Requires Python ≥ 3.12 (macOS recommended; the network sandbox layer uses `sandbox-exec`).
```bash
# 1) optional, once (needs network): install the isolated environment and the two models; it seals itself from the internet when it finishes
python3 -I scripts/buscador/preparar_profundo.py

# 2) search the sessions of the current project (default: light mode)
python3 -I scripts/buscador/buscar_sesiones.py "what did we decide about the weekly report format?" --excluir <current-session-uuid>
python3 -I scripts/buscador/buscar_sesiones.py "vague paraphrased question" --profundo      # deep mode
python3 -I scripts/buscador/buscar_sesiones.py "exact term" --solo-v2                         # no models
```
To use the directives and hook in your own project: copy `scripts/`, `.context/` and `plantillas/CLAUDE.md` (as `CLAUDE.md`) into it, merge `plantillas/settings.json` into `.claude/settings.json`, copy `skills/*` to `.claude/skills/`, and write your own directives following the format described at the top of `.context/directivas.md`. Then run `python3 -I scripts/directivas-buscador/directivas_buscador.py mapa`.

Environment variables: `BUSCADOR_HOME` (index/models location, default `~/.memoria-local`), `CLAUDE_PROJECT_DIR`, `BUSCADOR_ZONA` (time zone), `BUSCADOR_SIGLAS` (two-letter acronyms that count as words).

## Numbers (author's own history, 183 test questions, part written by Claude)
| Mode | Answer in top 5 | First result | MRR | Whole command |
|---|---|---|---|---|
| V2 only | 58 % | 38 % | 0.467 | ≈ 0.1 s |
| Light | 70 % | 54 % | ≈ 0.60 | ≈ 7 s |
| Deep | 73 % | 56 % | ≈ 0.63 | ≈ 9 s |
One person, one history: measure with your own questions (`scripts/buscador/evaluacion/evaluar_metodos.py`). Details and what did not work (a small home-grown model) in `docs/resultados.md`.

## Privacy
The index stores **everything you typed, unmasked** (passwords included if you pasted them). Keep `~/.memoria-local` private; never publish it. Models are open (MIT and Apache-2.0), pinned to a commit, hash-verified and read-only; searches run with network blocked in three layers (files, code, system). Limits are described honestly in `docs/seguridad-y-privacidad.md`.

## Tests
`python3 -I tests/smoke_test.py` builds a throw-away project and synthetic sessions in a temp folder and checks the date parser, search, directive map and hook. It never touches your real index.

## License
MIT. Third-party models keep their own licenses (MIT, Apache-2.0).
