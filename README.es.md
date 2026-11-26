# Memoria local para Claude Code

Búsqueda 100 % local en tus **conversaciones pasadas de Claude Code**, más un sistema de *directivas*, *memoria* y *skills* reutilizables que hace que Claude siga tus reglas con poco contexto. Nada sale de tu equipo mientras buscas; lo único que usa la red es instalar dos modelos abiertos, una sola vez.

> English: [README.md](README.md)

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
