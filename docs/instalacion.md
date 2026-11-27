# Manual de instalación · Installation manual

> 💡 **Pídele a tu Claude que te ayude con la instalación.** Abre Claude Code en tu proyecto y pega el mensaje de la sección «Mensaje para tu Claude».
> 💡 **Ask your Claude to help you install it.** Open Claude Code in your project and paste the message in the section "Message for your Claude".

---

# ESPAÑOL

## Mensaje para tu Claude (cópialo y pégalo)
```
Lee README.md y docs/instalacion.md de este repositorio y ayúdame a instalar la búsqueda local de conversaciones en mi proyecto.
Antes de ejecutar nada, dime qué vas a hacer. Los pasos con red son preparar_profundo.py (descarga unos 2 GB) y, solo si lo quiero, preparar_maximo.py (≈ 1.2 GB): pídeme confirmación antes de correrlos.
No modifiques mi CLAUDE.md ni mi .claude/settings.json sin mostrarme primero el cambio exacto, y no subas nada a internet.
Al terminar corre scripts/buscador/verificar_aislamiento.py y tests/smoke_test.py y cuéntame el resultado.
```

## 1. Requisitos
- **Claude Code** instalado y un proyecto donde ya hayas conversado (la búsqueda lee sus sesiones).
- **Python 3.12 o superior.** Comprueba con `python3 --version`; en macOS el de sistema suele ser más viejo: instala uno nuevo (por ejemplo `brew install python@3.12`) y usa `python3.12` en lugar de `python3` en todos los comandos de este manual.
- **Disco:** unos 2.5 GB para los modelos del Ligero y del Profundo, más ≈ 1.2 GB si agregas el Máximo (Qwen3); el Ultra ligero no necesita nada.
- **Red:** únicamente durante el paso 5 (instalar los modelos) y el 5b (agregar el Máximo). Después, los modelos quedan sin forma de conectarse.
- **Sistema:** **macOS: probado** (el bloqueo de red del sistema usa `sandbox-exec`). **Linux: no probado** (usa `unshare` o `bwrap`). **Windows: no compatible tal cual**, porque no hay aislamiento de red del sistema para él y el buscador se niega a correr los modelos sin él: solo sirve el modo `--solo-v2`, o **WSL2** (Linux dentro de Windows, también sin probar). Forzar `BUSCADOR_PERMITIR_SIN_SANDBOX=1` quita la capa de sistema y es menos seguro. GPU Apple opcional (más rápido).

## 2. Qué instalar: tres niveles
- **Ultra ligero (sin modelos):** copia `scripts/` y ya; usa `--ultraligero` (o `--solo-v2`). Rápido (≈ 0.1 s) pero de menor precisión.
- **Ligero y Profundo:** además instala los dos modelos (pasos 5 y 6). Ligero (≈ 3–7 s) y profundo (≈ 5–9 s).
- **Máximo (el mejor medido, opcional):** además agrega Qwen3-Reranker (paso 5b, ≈ 1.2 GB). Es el modo por defecto cuando está instalado (≈ 7–12 s).

## 3. Pasos
1. **Obtén el repo:** `git clone https://github.com/JonathanFVC/brain-optimized-memory-for-claude-code.git`
2. **Copia a tu proyecto** (en la carpeta de tu proyecto): `scripts/` → `scripts/`, `.context/` → `.context/`.
3. **Claude Code:** copia `plantillas/CLAUDE.md` como `CLAUDE.md` (si ya tienes uno, **mezcla** el contenido, no lo reemplaces); mezcla `plantillas/settings.json` en `.claude/settings.json` (los hooks); copia `skills/*` a `.claude/skills/`; opcional: `plantillas/memory/*` a `~/.claude/projects/<tu-proyecto>/memory/` (la ruta del proyecto es su ruta con los caracteres no alfanuméricos cambiados por `-`).
4. **Genera el mapa de directivas:** `python3.12 -I scripts/directivas-buscador/directivas_buscador.py mapa` (después edita `.context/directivas.md` con **tus** reglas; las de ejemplo son ficticias).
5. **Instala los modelos (con red, tarda varios minutos):** `python3.12 -I scripts/buscador/preparar_profundo.py`. Crea un entorno aislado en `~/.memoria-local/profundo`, descarga los dos modelos con commit fijado y huellas verificadas y, **al terminar, los sella solo contra internet** (si algo falla en el sellado, no queda marcada como lista).
5b. **(Opcional) Agrega el nivel Máximo (con red, ≈ 1.2 GB):** `python3.12 -I scripts/buscador/preparar_maximo.py`. Descarga `Qwen3-Reranker-0.6B` (Apache-2.0) con commit fijado y huellas verificadas, lo agrega al manifiesto, comprueba que funciona sin red (en el entorno sellado y dentro de `sandbox-exec`) y vuelve a sellar; si algo falla, deja la instalación como estaba.
6. **Verifica el aislamiento:** `python3.12 -I scripts/buscador/verificar_aislamiento.py` (debe terminar con «AISLADO: todo en orden») y la prueba de humo `python3.12 -I tests/smoke_test.py` (debe decir «TODO OK»).
7. **Primera búsqueda:** `python3.12 -I scripts/buscador/buscar_sesiones.py "algo que hayan hablado" --excluir <uuid de la sesión actual>`. La primera vez indexa tus sesiones (unos segundos) y, en profundo, vectoriza (≈ 40 s por cada 6,000 turnos).
8. **Reinicia Claude Code** para que cargue los hooks nuevos.
9. **(Opcional) Elige el modo base:** `python3.12 -I scripts/buscador/buscar_sesiones.py --modo ligero` (valores: `ultraligero`, `ligero`, `profundo`, `maximo`; sin valor muestra el actual). En macOS, un icono en la barra de menú hace lo mismo: `scripts/modo-barra-de-menu/construir.sh` y `open ~/.memoria-local/app/"Modo de busqueda.app"`; para que arranque al iniciar sesión, `scripts/modo-barra-de-menu/inicio-automatico.sh instalar`.

## 3 bis. Carpetas (qué hay que tener y qué se crea solo)
No hay carpetas nuevas obligatorias: la búsqueda de la carpeta (V1) funciona sobre **cualquier** carpeta de proyecto. Lo único que copias es lo del paso 2.
| Dónde | Qué es | ¿Hay que crearla? |
|---|---|---|
| `scripts/buscador/` y `scripts/directivas-buscador/` (en tu proyecto) | El código (V1, V2, `buscar_todo.py`, enrutador, hook) | Se copia en el paso 2 |
| `.context/` (en tu proyecto) | Directivas y palabras de disparo para el hook | Solo si usas directivas |
| `~/.memoria-local/` (o `BUSCADOR_HOME`) | **Fuera del proyecto**, carpeta privada (700): `sesiones.db` y `index.db` (índices), `profundo/` (entorno, modelos, vectores de conversaciones y de la carpeta), `uso/` (registro local y `informe_criterios.md`), `directivas-estado/` | **No**: se crea sola al buscar o al instalar |
| `docs/` (en tu proyecto) | Tus notas en Markdown. Opcional: una línea `> **Resumen:** …` bajo el título sube el documento en el ranking y se muestra con el resultado | Opcional |
| `.context/indice.md` | Índice curado opcional (plantilla: `plantillas/indice.ejemplo.md`) | Opcional |
| `.context/buscador-alias.tsv` | Sinónimos propios opcionales: `término<TAB>equivalente` por línea | Opcional |
La primera búsqueda con `buscar_todo.py` indexa tu carpeta y vectoriza sus trozos (≈ 2–3 min por cada 28,000 trozos y ≈ 60 MB en `~/.memoria-local/profundo/vectores_carpeta.db`, una sola vez; después solo lo nuevo o cambiado). Requiere los modelos de los pasos 5 y 6; sin ellos usa `buscar.py` (BM25) directamente: `python3.12 -I scripts/buscador/buscar.py "<pregunta>"`.

## 4. Variables de entorno (opcionales)
`BUSCADOR_HOME` (dónde viven índice y modelos; por defecto `~/.memoria-local`) · `CLAUDE_PROJECT_DIR` (proyecto cuyas sesiones se buscan) · `BUSCADOR_ZONA` (zona horaria, p. ej. `America/Bogota`) · `BUSCADOR_SIGLAS` (siglas de 2 letras que cuentan como palabra) · `BUSCADOR_PERMITIR_SIN_SANDBOX=1` (solo si no hay aislamiento del sistema; menos seguro).

## 5. Problemas frecuentes
| Síntoma | Causa probable | Qué hacer |
|:--|:--|:--|
| `SyntaxError` al correr un script | Python menor a 3.12 | Instala Python 3.12 y usa `python3.12` |
| `[ALTO] no hay forma de aislar la red…` | No hay `sandbox-exec`, `unshare` ni `bwrap` | En macOS no debería pasar; en Linux instala `bubblewrap` o usa `--solo-v2` |
| `pip` falla en el paso 5 | Sin red, proxy o poco disco | Revisa la conexión y el espacio (≈ 2.5 GB) y repite el paso |
| Aviso «el nivel Máximo no está instalado» | Falta Qwen3-Reranker | Corre `preparar_maximo.py` (con red) o usa `--profundo` |
| «ALTO: … alterado (huella distinta)» | Un archivo de modelo cambió | Reinstala: `preparar_profundo.py --reinstalar` |
| «Ya está instalado y AISLADO…» | Ya se instaló y se selló | Es normal; para actualizar usa `--reinstalar` |
| Las búsquedas no traen nada | No encuentra tus sesiones | Revisa `CLAUDE_PROJECT_DIR` o usa `--sesiones "~/.claude/projects/*"` |
| Termina con «→ Sugerencia: confianza baja» | Pregunta vaga o con otras palabras | Repite sin `--ligero` (usa el modo base) o con términos más específicos |
| Los hooks no se disparan | `settings.json` mal mezclado o Claude Code sin reiniciar | Revisa `.claude/settings.json` y reinicia |

## 6. Actualizar o desinstalar
- **Actualizar modelos o librerías:** `python3.12 -I scripts/buscador/preparar_profundo.py --reinstalar` (necesita red; retira el sello y lo vuelve a poner).
- **Desinstalar:** quita los hooks de `.claude/settings.json`, borra `scripts/` y `.context/` de tu proyecto y, para el índice y los modelos: en macOS `chflags -R nouchg ~/.memoria-local/profundo`; luego `chmod -R u+w ~/.memoria-local && rm -rf ~/.memoria-local`.
- **Quitar el icono (si lo instalaste):** `scripts/modo-barra-de-menu/inicio-automatico.sh quitar` y borra `~/.memoria-local/app`; hazlo antes de mover o borrar la carpeta del proyecto.

## 7. Privacidad (léelo)
`~/.memoria-local` contiene **una copia sin enmascarar de tus conversaciones**. No la subas, no la compartas y no la incluyas en repositorios. Más detalle en `docs/seguridad-y-privacidad.md`.

---

# ENGLISH

## Message for your Claude (copy and paste it)
```
Read README.md and docs/instalacion.md in this repository and help me install the local conversation search in my project.
Before running anything, tell me what you are going to do. The steps that use the network are preparar_profundo.py (about 2 GB) and, only if I want it, preparar_maximo.py (≈ 1.2 GB): ask me for confirmation before running them.
Do not modify my CLAUDE.md or my .claude/settings.json without first showing me the exact change, and do not upload anything to the internet.
When finished, run scripts/buscador/verificar_aislamiento.py and tests/smoke_test.py and tell me the result.
```

## 1. Requirements
- **Claude Code** installed and a project where you have already had conversations (the search reads its sessions).
- **Python 3.12 or newer.** Check with `python3 --version`; on macOS the system one is usually older: install a new one (e.g. `brew install python@3.12`) and use `python3.12` instead of `python3` in every command below.
- **Disk:** about 2.5 GB for the Light and Deep models, plus ≈ 1.2 GB if you add Max (Qwen3); Ultra-light needs nothing.
- **Network:** only during step 5 (installing the models) and 5b (adding Max). Afterwards the models have no way to connect.
- **System:** **macOS: tested** (the system-level network block uses `sandbox-exec`). **Linux: untested** (uses `unshare` or `bwrap`). **Windows: not supported as is**, because there is no system-level network isolation for it and the search refuses to run the models without it: only `--solo-v2` mode works, or **WSL2** (Linux inside Windows, also untested). Forcing `BUSCADOR_PERMITIR_SIN_SANDBOX=1` removes the system layer and is less safe. Apple GPU optional (faster).

## 2. What to install: three levels
- **Ultra-light (no models):** just copy `scripts/` and use `--ultraligero` (or `--solo-v2`). Fast (≈ 0.1 s) but less accurate.
- **Light and Deep:** also install the two models (steps 5 and 6). Light (≈ 3–7 s) and deep (≈ 5–9 s).
- **Max (best measured, optional):** also add Qwen3-Reranker (step 5b, ≈ 1.2 GB). It is the default mode when installed (≈ 7–12 s).

## 3. Steps
1. **Get the repo:** `git clone https://github.com/JonathanFVC/brain-optimized-memory-for-claude-code.git`
2. **Copy into your project** (in your project folder): `scripts/` → `scripts/`, `.context/` → `.context/`.
3. **Claude Code:** copy `plantillas/CLAUDE.md` as `CLAUDE.md` (if you already have one, **merge** it, do not replace it); merge `plantillas/settings.json` into `.claude/settings.json` (the hooks); copy `skills/*` to `.claude/skills/`; optional: `plantillas/memory/*` to `~/.claude/projects/<your-project>/memory/` (the project path is its path with non-alphanumeric characters replaced by `-`).
4. **Generate the directive map:** `python3.12 -I scripts/directivas-buscador/directivas_buscador.py mapa` (then edit `.context/directivas.md` with **your** rules; the examples are fictional).
5. **Install the models (needs network; takes several minutes):** `python3.12 -I scripts/buscador/preparar_profundo.py`. It creates an isolated environment in `~/.memoria-local/profundo`, downloads the two models with a pinned commit and verified hashes and, **when it finishes, seals them from the internet** (if sealing fails, the install is not marked as ready).
5b. **(Optional) Add the Max level (needs network, ≈ 1.2 GB):** `python3.12 -I scripts/buscador/preparar_maximo.py`. It downloads `Qwen3-Reranker-0.6B` (Apache-2.0) with a pinned commit and verified hashes, adds it to the manifest, checks it works offline (in the sealed environment and inside `sandbox-exec`) and seals again; if anything fails it leaves the install as it was.
6. **Verify the isolation:** `python3.12 -I scripts/buscador/verificar_aislamiento.py` (must end with "AISLADO: todo en orden") and the smoke test `python3.12 -I tests/smoke_test.py` (must say "TODO OK").
7. **First search:** `python3.12 -I scripts/buscador/buscar_sesiones.py "something you talked about" --excluir <current session uuid>`. The first time it indexes your sessions (a few seconds) and, in deep mode, builds vectors (≈ 40 s per 6,000 turns).
8. **Restart Claude Code** so it loads the new hooks.
9. **(Optional) Pick the base mode:** `python3.12 -I scripts/buscador/buscar_sesiones.py --modo ligero` (values: `ultraligero`, `ligero`, `profundo`, `maximo`; with no value it shows the current one). On macOS a menu-bar icon does the same: `scripts/modo-barra-de-menu/construir.sh` and `open ~/.memoria-local/app/"Modo de busqueda.app"`; to start it at login, `scripts/modo-barra-de-menu/inicio-automatico.sh instalar`.

## 3 bis. Folders (what you need and what is created by itself)
No new folder is mandatory: folder search (V1) works on **any** project folder. All you copy is what step 2 says.
| Where | What it is | Do I create it? |
|---|---|---|
| `scripts/buscador/` and `scripts/directivas-buscador/` (in your project) | The code (V1, V2, `buscar_todo.py`, router, hook) | Copied in step 2 |
| `.context/` (in your project) | Directives and trigger words for the hook | Only if you use directives |
| `~/.memoria-local/` (or `BUSCADOR_HOME`) | **Outside the project**, private folder (700): `sesiones.db` and `index.db` (indexes), `profundo/` (environment, models, conversation and folder vectors), `uso/` (local log and `informe_criterios.md`), `directivas-estado/` | **No**: it is created by itself when you search or install |
| `docs/` (in your project) | Your Markdown notes. Optional: a `> **Resumen:** …` line under the title raises the document in the ranking and is shown with the result | Optional |
| `.context/indice.md` | Optional curated index (template: `plantillas/indice.ejemplo.md`) | Optional |
| `.context/buscador-alias.tsv` | Optional own synonyms: `term<TAB>equivalent` per line | Optional |
The first `buscar_todo.py` search indexes your folder and vectorizes its chunks (≈ 2–3 min per 28,000 chunks and ≈ 60 MB in `~/.memoria-local/profundo/vectores_carpeta.db`, once; afterwards only what is new or changed). It needs the models from steps 5 and 6; without them use `buscar.py` (BM25) directly: `python3.12 -I scripts/buscador/buscar.py "<question>"`.

## 4. Environment variables (optional)
`BUSCADOR_HOME` (where the index and models live; default `~/.memoria-local`) · `CLAUDE_PROJECT_DIR` (project whose sessions are searched) · `BUSCADOR_ZONA` (time zone, e.g. `America/Bogota`) · `BUSCADOR_SIGLAS` (two-letter acronyms that count as words) · `BUSCADOR_PERMITIR_SIN_SANDBOX=1` (only if there is no system isolation; less safe).

## 5. Common problems
| Symptom | Likely cause | What to do |
|:--|:--|:--|
| `SyntaxError` when running a script | Python older than 3.12 | Install Python 3.12 and use `python3.12` |
| `[ALTO] no hay forma de aislar la red…` | No `sandbox-exec`, `unshare` or `bwrap` | Should not happen on macOS; on Linux install `bubblewrap` or use `--solo-v2` |
| `pip` fails in step 5 | No network, proxy or low disk | Check connection and space (≈ 2.5 GB) and repeat the step |
| Warning "el nivel Máximo no está instalado" | Qwen3-Reranker is missing | Run `preparar_maximo.py` (needs network) or use `--profundo` |
| "ALTO: … alterado (huella distinta)" | A model file changed | Reinstall: `preparar_profundo.py --reinstalar` |
| "Ya está instalado y AISLADO…" | Already installed and sealed | Normal; to update use `--reinstalar` |
| Searches return nothing | It cannot find your sessions | Check `CLAUDE_PROJECT_DIR` or use `--sesiones "~/.claude/projects/*"` |
| Ends with "→ Sugerencia: confianza baja" | Vague or differently worded question | Repeat without `--ligero` (it uses the base mode) or with more specific terms |
| Hooks do not fire | `settings.json` merged wrongly or Claude Code not restarted | Check `.claude/settings.json` and restart |

## 6. Update or uninstall
- **Update models or libraries:** `python3.12 -I scripts/buscador/preparar_profundo.py --reinstalar` (needs network; removes the seal and puts it back).
- **Uninstall:** remove the hooks from `.claude/settings.json`, delete `scripts/` and `.context/` from your project and, for the index and models: on macOS `chflags -R nouchg ~/.memoria-local/profundo`; then `chmod -R u+w ~/.memoria-local && rm -rf ~/.memoria-local`.
- **Remove the icon (if you installed it):** `scripts/modo-barra-de-menu/inicio-automatico.sh quitar` and delete `~/.memoria-local/app`; do it before moving or deleting the project folder.

## 7. Privacy (read this)
`~/.memoria-local` holds **an unmasked copy of your conversations**. Do not upload it, share it or include it in repositories. More detail in `docs/seguridad-y-privacidad.md`.
