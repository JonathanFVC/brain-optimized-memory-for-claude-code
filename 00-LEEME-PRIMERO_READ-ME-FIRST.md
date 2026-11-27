# 🚀 Dale este zip a tu Claude · Give this zip to your Claude

**🇲🇽 Español:** abre Claude Code en **tu proyecto**, pon este zip (o la carpeta ya descomprimida) donde Claude pueda leerlo y pégale esto:

```
Lee 00-LEEME-PRIMERO_READ-ME-FIRST.md de este zip y haz la instalación y los ajustes necesarios en mi proyecto, paso a paso.
Antes de ejecutar nada dime tu plan. Pídeme confirmación antes de cualquier descarga o cambio a mis archivos de configuración, y no subas nada a internet.
```

**🇬🇧 English:** open Claude Code in **your project**, put this zip (or the already unzipped folder) where Claude can read it and paste this:

```
Read 00-LEEME-PRIMERO_READ-ME-FIRST.md in this zip and do the installation and the necessary adjustments in my project, step by step.
Before running anything, tell me your plan. Ask me for confirmation before any download or any change to my configuration files, and do not upload anything to the internet.
```

> Todo corre en tu equipo; no se envía nada a ningún servidor. / Everything runs on your machine; nothing is sent to any server.
> Tu Claude hace el trabajo; tú solo confirmas. / Your Claude does the work; you only confirm.

---

# ESPAÑOL

## 0. Qué es esto
Una búsqueda **100 % local** para Claude Code: encuentra lo que ya hablaron (**V2**, conversaciones pasadas) y lo que ya está escrito en tu proyecto (**V1**, archivos), con un **enrutador** que decide cuál usar en cada tarea y se **autocalibra con el uso**. Este zip trae todo: código, modelos (se descargan con un script verificado), aislamiento de red, plantillas, skills, pruebas y manuales.

## 1. Reglas para Claude (cúmplelas siempre)
1. **Plan primero.** Antes de ejecutar nada, dile al usuario qué vas a hacer, en qué carpetas y qué archivos tocarás.
2. **Confirmación antes de:** (a) cualquier descarga (`preparar_profundo.py` ≈ 2 GB; `preparar_maximo.py` ≈ 1.2 GB), (b) tocar `CLAUDE.md`, `.claude/settings.json` u otros archivos que ya existan, (c) instalar programas del sistema (por ejemplo Python con `brew`).
3. **Respaldo y diferencia.** Si un archivo ya existe, haz una copia `*.bak`, **muestra la diferencia exacta** y mezcla; nunca lo reemplaces sin permiso.
4. **No uses `sudo`**, no subas nada a internet, no ejecutes scripts que no estén en este documento y no salgas de: la carpeta del proyecto, la carpeta de este zip y `~/.memoria-local/` (carpeta de datos, privada).
5. **Si un paso falla, detente**, cuéntalo con el mensaje exacto y consulta `docs/instalacion.md` § 5; no improvises ni uses atajos que quiten el aislamiento (por ejemplo `BUSCADOR_PERMITIR_SIN_SANDBOX=1` solo si el usuario lo pide y entiende el riesgo).
6. **Al terminar**, entrega un resumen: qué se copió y dónde, qué se modificó (con las copias `*.bak`), qué se descargó, resultados de las pruebas y cómo desinstalar.

## 2. Pregunta primero al usuario (una sola vez, con opciones)
- **Nivel:** *Ultra ligero* (sin modelos, 0 descargas, menor precisión) · *Ligero + Profundo* (≈ 2.5 GB, recomendado) · *Máximo* (además ≈ 1.2 GB; el mejor medido).
- **Proyecto:** la ruta de la carpeta donde se instalará (la actual por defecto).
- **Sistema:** macOS está **probado**; Linux sin probar; Windows solo con `--solo-v2` o WSL2 (ver `docs/instalacion.md` § 1).

## 3. Pasos (en orden)
**Paso 1 · Revisar el entorno.** `python3 --version` (hace falta **3.12 o superior**; si no, propón `brew install python@3.12` y usa `python3.12` en todo lo demás), `uname -s` y `df -h ~` (espacio libre ≥ 3 GB para Ligero + Profundo). Guarda la ruta absoluta del intérprete: `command -v python3.12 || command -v python3`.

**Paso 2 · Ubicar el zip descomprimido.** Si te dieron el `.zip`, descomprímelo en una carpeta temporal (por ejemplo `~/memoria-local-para-claude`). En lo que sigue, `<ZIP>` es esa carpeta y `<PROYECTO>` la del usuario.

**Paso 3 · Copiar el código (sin pisar nada).**
```
mkdir -p <PROYECTO>/scripts <PROYECTO>/docs <PROYECTO>/.context <PROYECTO>/.claude/skills
rsync -a <ZIP>/scripts/buscador/ <PROYECTO>/scripts/buscador/
rsync -a <ZIP>/scripts/directivas-buscador/ <PROYECTO>/scripts/directivas-buscador/
cp -n <ZIP>/docs/criterio-busqueda.md <ZIP>/docs/seguridad-y-privacidad.md <PROYECTO>/docs/
rsync -a <ZIP>/skills/ <PROYECTO>/.claude/skills/
```
Para `.context/`: si el usuario **ya tiene** `.context/directivas.md`, **no lo reemplaces** (muestra las directivas de ejemplo de `<ZIP>/.context/` y ofrece agregar solo las que quiera); si no lo tiene, copia `<ZIP>/.context/` completo (las directivas de ejemplo son ficticias: invita a editarlas).

**Paso 4 · Conectar con Claude Code (con permiso y diferencia).**
- `CLAUDE.md`: si no existe, copia `<ZIP>/plantillas/CLAUDE.md`; si existe, **mezcla** esas líneas al final (muestra el cambio).
- `.claude/settings.json`: agrega los *hooks* de `<ZIP>/plantillas/settings.json` (`SessionStart` y `UserPromptSubmit`) **sin borrar los que ya haya**. **Importante:** en esos comandos cambia `python3` por la **ruta absoluta del intérprete 3.12+** del Paso 1. Valida que el JSON quede correcto (`python3.12 -c "import json,sys; json.load(open(sys.argv[1]))" .claude/settings.json`).
- Opcional (pregunta): `<ZIP>/plantillas/memory/*` a `~/.claude/projects/<ruta-del-proyecto-con-guiones>/memory/` (la ruta del proyecto con cada carácter no alfanumérico cambiado por `-`).

**Paso 5 · Generar el mapa de directivas.** Desde `<PROYECTO>`: `python3.12 -I scripts/directivas-buscador/directivas_buscador.py mapa`.

**Paso 6 · Carpeta de datos (se crea sola).** `~/.memoria-local/` (privada, permisos 700) guarda índices, modelos, vectores y el registro de uso. **No la crees a mano** y no la subas ni la compartas: contiene una copia sin enmascarar de las conversaciones. Se puede cambiar con `BUSCADOR_HOME`.

**Paso 7 · Modelos y aislamiento** *(solo Ligero + Profundo o Máximo; con confirmación y red)*.
1. `python3.12 -I scripts/buscador/preparar_profundo.py` — crea un entorno aislado en `~/.memoria-local/profundo`, descarga los dos modelos con **commit fijado y huellas SHA-256 verificadas**, los guarda **sin código ejecutable** y, **al terminar, los sella contra internet**: bloqueo de red dentro de Python, bloqueo del sistema (`sandbox-exec` en macOS) y archivos inmutables. Si el sellado falla, no queda marcada como lista.
2. *(Máximo)* `python3.12 -I scripts/buscador/preparar_maximo.py` — agrega Qwen3-Reranker-0.6B con el mismo método y vuelve a sellar; si algo falla, deja la instalación como estaba.
3. **Verifica el aislamiento:** `python3.12 -I scripts/buscador/verificar_aislamiento.py` debe terminar con «AISLADO: todo en orden». Si no, **no continúes**: repórtalo.
*(Ultra ligero: sáltate este paso; usa `--ultraligero`.)*

**Paso 8 · Pruebas** (sin red, con datos ficticios). Desde `<ZIP>`: `python3.12 -I tests/smoke_test.py` («TODO OK»), `tests/test_enrutador.py`, `tests/test_calibrador.py` y `tests/test_modo.py` (cada una debe terminar en «TODO OK»). Comprueba que lo instalado es lo mismo: `diff -r <ZIP>/scripts/buscador <PROYECTO>/scripts/buscador` (sin diferencias, salvo `__pycache__`).

**Paso 9 · Primera búsqueda.** `python3.12 -I scripts/buscador/buscar_sesiones.py "algo que hayan hablado" --excluir <uuid de la sesión actual>` (la primera vez indexa las sesiones; en profundo también vectoriza) y `python3.12 -I scripts/buscador/buscar_todo.py "una tarea de tu proyecto" --explica` (solo muestra qué decidiría el enrutador).

**Paso 10 · Reiniciar Claude Code** para que cargue los hooks, y avisar al usuario.

## 4. El enrutador se autocalibra (no hay nada que instalar)
De inicio el enrutador busca **siempre en V1 + V2** (salvo saludos, imágenes sueltas y pedidos vagos). Cuando tú (Claude) detectes que se cumplieron los criterios de una tarea, la **marcas** con `buscar_todo.py --marca v1|v2|ambas|ninguna <tarea> [--id <búsqueda>]` (la fuente que de verdad aportó; no al terminar la conversación; una marca por tarea). Con ≈ 25 marcas coherentes por regla (≈ 1,000 en total para las reglas frecuentes) cada regla elige sola **solo V1, solo V2, las dos o en vivo (sin buscar)**. Ver el estado: `buscar_todo.py --calibracion`. **Disclaimer para el usuario:** la precisión mejora con el uso; al inicio gasta más tokens pero es completa y segura. Si el usuario pregunta si se puede **ajustar** el enrutador, responde que sí y sigue la skill `ajustar-enrutador` (por etapas). Variables útiles: `BUSCADOR_PRIOR=reglas` (parte de las reglas validadas del autor), `BUSCADOR_CALIBRACION=0` (apaga el calibrado).

## 5. Lista de verificación final (marca cada una)
- [ ] Python 3.12+ identificado y usado en los hooks.
- [ ] `scripts/buscador/` y `scripts/directivas-buscador/` copiados; `diff -r` limpio.
- [ ] `CLAUDE.md` y `.claude/settings.json` mezclados (con `*.bak` y diferencia mostrada), JSON válido.
- [ ] Skills en `.claude/skills/` (`buscar-conversaciones`, `trazabilidad`, `actualizar-directivas`, `ajustar-enrutador`).
- [ ] `.context/` con directivas (propias o de ejemplo) y mapa generado.
- [ ] *(Ligero/Profundo/Máximo)* modelos instalados, **sellados** y `verificar_aislamiento.py` en «AISLADO: todo en orden».
- [ ] Pruebas en «TODO OK».
- [ ] Primera búsqueda hecha y Claude Code reiniciado.
- [ ] Resumen entregado al usuario, con el aviso de privacidad de `~/.memoria-local`.

## 6. Si algo falla / actualizar / desinstalar
`docs/instalacion.md` (§ 5 problemas frecuentes y § 6 actualizar y desinstalar) y `docs/seguridad-y-privacidad.md`. Desinstalar = quitar los hooks, borrar `scripts/` y `.context/` copiados y, en macOS, `chflags -R nouchg ~/.memoria-local/profundo && chmod -R u+w ~/.memoria-local && rm -rf ~/.memoria-local`.

---

# ENGLISH

## 0. What is this
A **100 % local** search for Claude Code: it finds what you already discussed (**V2**, past conversations) and what is already written in your project (**V1**, files), with a **router** that decides which to use for each task and **calibrates itself with use**. This zip has everything: code, models (downloaded with a verified script), network isolation, templates, skills, tests and manuals.

## 1. Rules for Claude (always follow them)
1. **Plan first.** Before running anything, tell the user what you will do, in which folders and which files you will touch.
2. **Ask for confirmation before:** (a) any download (`preparar_profundo.py` ≈ 2 GB; `preparar_maximo.py` ≈ 1.2 GB), (b) touching `CLAUDE.md`, `.claude/settings.json` or any other file that already exists, (c) installing system software (for example Python with `brew`).
3. **Backup and diff.** If a file already exists, make a `*.bak` copy, **show the exact difference** and merge; never replace it without permission.
4. **No `sudo`**, no uploading anything to the internet, no running scripts that are not in this document, and stay within: the project folder, this zip's folder and `~/.memoria-local/` (private data folder).
5. **If a step fails, stop**, report the exact message and check `docs/instalacion.md` § 5; do not improvise or use shortcuts that remove the isolation (for example `BUSCADOR_PERMITIR_SIN_SANDBOX=1` only if the user asks and understands the risk).
6. **When finished**, hand over a summary: what was copied and where, what was modified (with the `*.bak` copies), what was downloaded, test results and how to uninstall.

## 2. Ask the user first (once, with options)
- **Level:** *Ultra-light* (no models, 0 downloads, lower accuracy) · *Light + Deep* (≈ 2.5 GB, recommended) · *Max* (plus ≈ 1.2 GB; best measured).
- **Project:** the path of the folder where it will be installed (the current one by default).
- **System:** macOS is **tested**; Linux untested; Windows only with `--solo-v2` or WSL2 (see `docs/instalacion.md` § 1).

## 3. Steps (in order)
**Step 1 · Check the environment.** `python3 --version` (**3.12 or newer** is required; otherwise propose `brew install python@3.12` and use `python3.12` everywhere below), `uname -s` and `df -h ~` (free space ≥ 3 GB for Light + Deep). Keep the absolute path of the interpreter: `command -v python3.12 || command -v python3`.

**Step 2 · Locate the unzipped folder.** If you were given the `.zip`, unzip it into a temporary folder (e.g. `~/memoria-local-para-claude`). Below, `<ZIP>` is that folder and `<PROJECT>` is the user's.

**Step 3 · Copy the code (without overwriting anything).**
```
mkdir -p <PROJECT>/scripts <PROJECT>/docs <PROJECT>/.context <PROJECT>/.claude/skills
rsync -a <ZIP>/scripts/buscador/ <PROJECT>/scripts/buscador/
rsync -a <ZIP>/scripts/directivas-buscador/ <PROJECT>/scripts/directivas-buscador/
cp -n <ZIP>/docs/criterio-busqueda.md <ZIP>/docs/seguridad-y-privacidad.md <PROJECT>/docs/
rsync -a <ZIP>/skills/ <PROJECT>/.claude/skills/
```
For `.context/`: if the user **already has** `.context/directivas.md`, **do not replace it** (show the example directives in `<ZIP>/.context/` and offer to add only the ones they want); if not, copy `<ZIP>/.context/` as a whole (the example directives are fictional: invite them to edit them).

**Step 4 · Connect with Claude Code (with permission and a diff).**
- `CLAUDE.md`: if it does not exist, copy `<ZIP>/plantillas/CLAUDE.md`; if it exists, **merge** those lines at the end (show the change).
- `.claude/settings.json`: add the *hooks* from `<ZIP>/plantillas/settings.json` (`SessionStart` and `UserPromptSubmit`) **without removing existing ones**. **Important:** in those commands replace `python3` with the **absolute path of the 3.12+ interpreter** from Step 1. Validate the JSON (`python3.12 -c "import json,sys; json.load(open(sys.argv[1]))" .claude/settings.json`).
- Optional (ask): `<ZIP>/plantillas/memory/*` to `~/.claude/projects/<project-path-with-dashes>/memory/` (the project path with every non-alphanumeric character replaced by `-`).

**Step 5 · Generate the directive map.** From `<PROJECT>`: `python3.12 -I scripts/directivas-buscador/directivas_buscador.py mapa`.

**Step 6 · Data folder (created by itself).** `~/.memoria-local/` (private, mode 700) holds indexes, models, vectors and the usage log. **Do not create it by hand** and do not upload or share it: it holds an unmasked copy of the conversations. It can be changed with `BUSCADOR_HOME`.

**Step 7 · Models and isolation** *(Light + Deep or Max only; with confirmation and network)*.
1. `python3.12 -I scripts/buscador/preparar_profundo.py` — creates an isolated environment in `~/.memoria-local/profundo`, downloads the two models with a **pinned commit and verified SHA-256 hashes**, stores them **without executable code** and, **when it finishes, seals them from the internet**: network block inside Python, system-level block (`sandbox-exec` on macOS) and immutable files. If sealing fails, it is not marked as ready.
2. *(Max)* `python3.12 -I scripts/buscador/preparar_maximo.py` — adds Qwen3-Reranker-0.6B the same way and seals again; if anything fails, it leaves the install as it was.
3. **Verify the isolation:** `python3.12 -I scripts/buscador/verificar_aislamiento.py` must end with "AISLADO: todo en orden". If not, **do not continue**: report it.
*(Ultra-light: skip this step; use `--ultraligero`.)*

**Step 8 · Tests** (no network, fictional data). From `<ZIP>`: `python3.12 -I tests/smoke_test.py` ("TODO OK"), `tests/test_enrutador.py`, `tests/test_calibrador.py` and `tests/test_modo.py` (each must end in "TODO OK"). Check that what is installed is the same: `diff -r <ZIP>/scripts/buscador <PROJECT>/scripts/buscador` (no differences, except `__pycache__`).

**Step 9 · First search.** `python3.12 -I scripts/buscador/buscar_sesiones.py "something you talked about" --excluir <current session uuid>` (the first time it indexes the sessions; in deep mode it also builds vectors) and `python3.12 -I scripts/buscador/buscar_todo.py "a task from your project" --explica` (only shows what the router would decide).

**Step 10 · Restart Claude Code** so it loads the hooks, and tell the user.

## 4. The router calibrates itself (nothing to install)
At first the router **always searches V1 + V2** (except greetings, bare images and vague requests). When you (Claude) detect that a task's criteria are met, **mark** it with `buscar_todo.py --marca v1|v2|ambas|ninguna <task> [--id <search>]` (the source that really helped; not when the conversation ends; one mark per task). With ≈ 25 consistent marks per rule (≈ 1,000 in total for the frequent rules) each rule picks on its own **V1 only, V2 only, both, or live (no search)**. See the status: `buscar_todo.py --calibracion`. **Disclaimer for the user:** accuracy improves with use; at first it spends more tokens but is complete and safe. If the user asks whether the router can be **adjusted**, answer yes and follow the `ajustar-enrutador` skill (in stages). Useful variables: `BUSCADOR_PRIOR=reglas` (start from the author's validated rules), `BUSCADOR_CALIBRACION=0` (turns calibration off).

## 5. Final checklist (tick each one)
- [ ] Python 3.12+ identified and used in the hooks.
- [ ] `scripts/buscador/` and `scripts/directivas-buscador/` copied; clean `diff -r`.
- [ ] `CLAUDE.md` and `.claude/settings.json` merged (with `*.bak` and diff shown), valid JSON.
- [ ] Skills in `.claude/skills/` (`buscar-conversaciones`, `trazabilidad`, `actualizar-directivas`, `ajustar-enrutador`).
- [ ] `.context/` with directives (own or examples) and the map generated.
- [ ] *(Light/Deep/Max)* models installed, **sealed**, and `verificar_aislamiento.py` at "AISLADO: todo en orden".
- [ ] Tests at "TODO OK".
- [ ] First search done and Claude Code restarted.
- [ ] Summary delivered to the user, with the privacy notice about `~/.memoria-local`.

## 6. If something fails / update / uninstall
`docs/instalacion.md` (§ 5 common problems and § 6 update and uninstall) and `docs/seguridad-y-privacidad.md`. Uninstall = remove the hooks, delete the copied `scripts/` and `.context/` and, on macOS, `chflags -R nouchg ~/.memoria-local/profundo && chmod -R u+w ~/.memoria-local && rm -rf ~/.memoria-local`.
