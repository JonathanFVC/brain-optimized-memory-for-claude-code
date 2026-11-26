# Local memory for Claude Code

100 % local search over your **past Claude Code conversations**, plus a small system of reusable *directives*, *memory* and *skills* that keeps Claude following your rules with little context. Nothing leaves your machine while you search; the only step that uses the network is installing two open models once.

> Español: [README.es.md](README.es.md)

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
