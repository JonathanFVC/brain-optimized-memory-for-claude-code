# Arquitectura del buscador de conversaciones

> **Resumen:** V2 (BM25 sobre palabras y prefijos, fusión RRF, fechas en español, SQLite FTS5, solo biblioteca estándar) genera candidatos; modelos abiertos y locales los reordenan (ligero), suman candidatos por significado (profundo) y un segundo reordenador reordena los 5 mejores (máximo); todo sin red.

## Piezas
- **`scripts/buscador/buscar_sesiones.py` (V2 y lanzador):** lee los `.jsonl` de las sesiones de Claude Code, arma un turno por cada mensaje del usuario más el texto de Claude hasta el siguiente mensaje, y lo indexa en SQLite FTS5 (fuera del proyecto). Busca con BM25 sobre palabras y con BM25 sobre prefijos de 5 letras (une «transcripción/transcribir»), fusiona las listas con RRF, aplica tope de 2 resultados por sesión y une duplicados. Si la pregunta trae palabras de SQL o comandos, también busca en las entradas y resultados de herramientas. Entiende fechas en español.
- **`scripts/buscador/buscar_profundo.py` (modos con modelos):** corre con el Python de un entorno aislado. **Ligero** = V2 trae los 20 mejores y `gte-multilingual-reranker-base` los reordena leyendo pregunta y turno juntos. **Profundo** = además suma candidatos por significado con vectores de `multilingual-e5-small` (guardados una vez por turno, ≈ 6 ms cada uno) y fusiona con RRF antes de reordenar. **Máximo** = además `Qwen3-Reranker-0.6B` reordena los 5 mejores que dejó gte y se promedian los puntajes (z dentro de esos 5).
- **`preparar_profundo.py` / `descargar_modelos_profundo.py`:** instalan el entorno y los dos primeros modelos (con red), con commit fijado, solo archivos de texto/json/safetensors, huellas SHA-256 contra la API de Hugging Face y modelos de solo lectura; **al terminar blindan la instalación automáticamente** (entorno sin forma de conectarse, comprobado; ver `seguridad-y-privacidad.md`).
- **`preparar_maximo.py`:** agrega `Qwen3-Reranker-0.6B` a una instalación ya sellada (con red, mismas garantías: commit fijado, huellas, sin código remoto), comprueba que carga y puntúa sin red (en el entorno sellado y dentro de `sandbox-exec`), actualiza el manifiesto y vuelve a sellar; si falla, deja la instalación como estaba.
- **Modo base (`modo`, `--modo`, icono de la barra de menú):** un archivo de una línea (`ultraligero | ligero | profundo | maximo`) en la carpeta de datos; toda búsqueda sin bandera lo usa (sin archivo: Máximo si está instalado, si no Profundo). Una bandera explícita manda sobre él. El icono (`scripts/modo-barra-de-menu/`, solo macOS) lo lee y lo escribe; `--modo` lo hace desde cualquier sistema.
- **`verificar_aislamiento.py`:** comprueba cuando quieras que la instalación sigue aislada (marca de instalación, entorno sin red, modelos sin código, huellas SHA-256 y aislamiento del sistema).
- **Registro de uso local:** `--util N` / `--inutil N` marcan si un fragmento sirvió; `--uso-stats` resume. Sirve para medir con uso real qué modo conviene.

## Cadena de respaldo
máximo → (si falta Qwen3) profundo → (si fallan los vectores) ligero → (si el modo está instalado pero falla) error, **sin** devolver resultados de menor precisión. V2 solo (modo ultra ligero) existe como `--ultraligero` / `--solo-v2`, si el usuario lo elige como modo base (con alerta) o cuando el modo con modelos no está instalado (con alerta).

## Tiempos medidos (Mac con GPU Apple; la primera vez de cada comando carga torch)
Comando completo: ultra ligero ≈ 0.1 s · ligero ≈ 3–7 s · profundo ≈ 5–9 s · máximo ≈ 7–12 s (de una Mac libre a una con carga). Con los modelos ya cargados: ≈ 0.4 s (profundo) y ≈ 1.0 s (máximo). Vectorizar un índice de ≈ 6,000 turnos la primera vez: ≈ 40 s.

## Variables de entorno
`BUSCADOR_HOME` (dónde viven índice, modelos y registro; por defecto `~/.memoria-local`) · `CLAUDE_PROJECT_DIR` (proyecto cuyas sesiones se buscan; por defecto el directorio actual) · `BUSCADOR_ZONA` (zona horaria de los días, p. ej. `America/Bogota`; por defecto la del sistema) · `BUSCADOR_SIGLAS` (siglas de dos letras que cuentan como palabra, p. ej. `ci,qa`).

## Qué sesiones busca
Por defecto, las del proyecto actual (`~/.claude/projects/<ruta del proyecto con no alfanuméricos → ->`). Para todas: `--sesiones "~/.claude/projects/*"`.

## Requisitos
Python 3.12 o superior. Para los modos con modelos: unos GB de disco (entorno con torch + 1.1 GB de modelos, y 1.2 GB más para el Máximo) y, de preferencia, GPU Apple (MPS); en CPU funciona más lento. La capa de sistema contra la red usa `sandbox-exec` (macOS); en otros sistemas quedan las capas de archivos y de código (ver `seguridad-y-privacidad.md`).
