# Seguridad y privacidad

> **Resumen:** todo corre en tu equipo; los modelos son abiertos, de solo lectura y verificados por huella; la red se bloquea en tres capas durante las búsquedas. El índice es una copia sensible de tus conversaciones: no se comparte.

## Qué es sensible aquí
- **El índice (`~/.memoria-local/sesiones.db`) y los vectores:** guardan el texto de tus conversaciones **sin enmascarar** (contraseñas incluidas, si las pegaste). Carpeta 700, archivos 600. No los copies, subas ni compartas. `--ocultar` solo enmascara al mostrar resultados.
- **El registro de uso** (`uso/`): ids y posiciones, no texto, pero revela qué buscas.
- **Tus directivas y memorias:** suelen describir tu trabajo. Este repositorio trae solo ejemplos ficticios; antes de publicar un repo propio que las incluya, revísalas.

## Modelos (solo abiertos y sin código ejecutable)
`intfloat/multilingual-e5-small` (MIT) y `Alibaba-NLP/gte-multilingual-reranker-base` (Apache-2.0) y, opcional para el modo Máximo, `Qwen/Qwen3-Reranker-0.6B` (Apache-2.0, agregado con `preparar_maximo.py` con las mismas garantías y vuelto a sellar), con **commit fijado** y huellas SHA-256 verificadas contra la API de Hugging Face. El descargador acepta solo texto, json y safetensors (nada de `.bin`, `.py`, onnx ni pickle) y se comprueba que los repos no traigan código (`auto_map`). Antes de cambiar un modelo o un commit, revísalo igual.

## Aislamiento automático al instalar (los modelos no pueden conectarse jamás)
Al terminar `preparar_profundo.py` se ejecuta un **blindaje** automático y la instalación solo queda marcada (`aislado.ok`) si todo pasa: (1) los modelos no traen código ejecutable; (2) se instalan `aislar_red.pth` y `aislar_red.py` en el entorno: **cualquier uso de ese Python, aun con `-I` y sin pasar por `buscar_sesiones.py`, tiene la red bloqueada** (conexiones, DNS, UDP, `urllib`) y fuerza el modo sin conexión de Hugging Face; (3) se comprueba que los sockets están bloqueados y que los dos modelos cargan y funcionan sin red; (4) en macOS se comprueba que `sandbox-exec` bloquea aun una conexión de bajo nivel que salta el bloqueo de Python y los archivos de los modelos se marcan de solo lectura e **inmutables** (`chflags uchg`). Volver a correr el instalador no hace nada; para reinstalar o actualizar hay que pedirlo con `--reinstalar` (necesita red, retira el aislamiento y lo vuelve a poner al terminar). Para comprobarlo cuando quieras: `python3 -I scripts/buscador/verificar_aislamiento.py`.
**Falla cerrado:** si el sistema no ofrece aislamiento de red (`sandbox-exec` en macOS; `unshare` o `bwrap` en Linux, **no probado en Linux**), `buscar_sesiones.py` se niega a correr los modelos; solo con `BUSCADOR_PERMITIR_SIN_SANDBOX=1` corren con las capas de archivos y de código (menos seguro).

## Sin red, tres capas (durante las búsquedas)
1. **Archivos:** modelos en carpeta de solo lectura con `manifiesto.json` (tamaño, fecha y SHA-256); si algo cambió, se recalcula la huella y, si no coincide, se aborta.
2. **Código:** `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1` antes de importar las librerías, carga solo desde rutas locales (`local_files_only=True`) y bloqueo de los sockets de red de Python (los de archivo local no). `buscar_profundo.py --probar-sin-red` lo comprueba.
3. **Sistema:** el lanzador corre todo dentro de `sandbox-exec` con `(deny network*)` (macOS) o `unshare -rn` / `bwrap --unshare-net` (Linux, no probado); si no hay ninguno, se niega a correr los modelos.
**Límite honesto:** `sandbox-exec` está marcado como obsoleto en macOS (funciona hoy); en otros sistemas no existe. Las capas 1 y 2 son barreras prácticas contra accidentes y comportamientos por defecto de las librerías, **no** contra código malicioso decidido a evadirlas. La única parte con red es la instalación (`preparar_profundo.py` y `preparar_maximo.py`; después de la primera vez, solo con `--reinstalar` o al agregar el Máximo); el Python del entorno queda bloqueado al terminarla.

## Si vas a publicar un repo propio basado en esto
Revisa árbol, nombres de archivo e historial completo (`git log --all -p`) en busca de rutas de tu equipo, nombres de tu empresa o clientes, tickets, correos, tokens y llaves; usa el correo `noreply` de GitHub para los commits; no subas índices (`*.db`), sesiones (`*.jsonl`) ni tus directivas o memorias reales. Lo publicado no se retira del todo (los commits siguen accesibles por su SHA).
