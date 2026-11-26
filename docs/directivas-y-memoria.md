# Directivas, memoria y el hook por mensaje

> **Resumen:** un archivo de directivas largo no se carga entero: se carga un mapa corto y un hook inyecta, en cada mensaje, las directivas y memorias más afines; así Claude Code sigue reglas largas con poco contexto.

## Idea
`CLAUDE.md` carga siempre `.context/directivas-mapa.md`: el **núcleo íntegro** (la directiva máxima, las prioritarias `P1`–`P4` y las secciones 2 y 3) y **una fila por directiva** con su línea en `directivas.md`. La directiva máxima obliga a preguntarse antes de cada acción si cae en alguna fila y, si cae, leer ese apartado completo. Además, el hook `UserPromptSubmit` puntúa cada mensaje contra todas las directivas (BM25 con palabras de disparo curadas) y contra las memorias, e inyecta las más afines **la primera vez que aparecen en la sesión**.

## Archivos
- `.context/directivas.md`: las reglas (ejemplo incluido; formato descrito al inicio del archivo).
- `.context/directivas-disparadores.tsv`: `fragmento del título<TAB>palabras` con las que se describe la situación (sube la afinidad).
- `.context/directivas-historial.md`: texto superado, movido textual.
- `.context/directivas-mapa.md`: **generado** (`directivas_buscador.py mapa`); no se edita ni se sube (está en `.gitignore`).
- Memoria: `~/.claude/projects/<proyecto>/memory/` (ejemplos en `plantillas/memory/`), con `MEMORY.md` como índice.

## Presupuesto de inyección (decisiones medidas)
- **Por mensaje:** hasta 3 directivas y 2 memorias, 8,000 caracteres de directivas como máximo; **por sesión:** 60 mil caracteres de texto completo y después solo punteros; 90 mil en total y después el hook calla.
- **Sin procedencia:** al inyectar se omiten las notas `_( … )_` (fecha, motivo, cita textual; ≈ 21 % del texto); siguen completas en el archivo y se deja una marca.
- **Tope por directiva de 6,000 caracteres** (antes 2,600: cortaba 14 de 88 directivas del autor, incluidas las más importantes; en 110 mensajes simulados, 46 recibían alguna cortada; ahora 0 con el mismo gasto).
- **Memorias:** el puntaje da un bono por cada palabra del mensaje que está en el nombre de la memoria; además se inyecta una memoria cuya frase entre « » o comillas coincide con una del mensaje; las siglas definidas en `BUSCADOR_SIGLAS` cuentan como palabra.
- **Índice de memoria en forma corta:** `- archivo.md` en lugar de `- [archivo](archivo.md)`: la mitad de bytes con el mismo contenido (el nombre del archivo ya es el título).

## Comandos
`directivas_buscador.py mapa` (regenera el mapa) · `hook` (lo usa Claude Code) · `buscar "texto"` (prueba a mano) · `guarda` (compara directivas contra el mapa y prueba el hook) · `memoria [--aplicar]` (normaliza `MEMORY.md`) · `evalmem` (mide la recuperación de memorias con `scripts/directivas-buscador/evaluacion/memoria_consultas.tsv`) · `actualizar antes|despues` (mecánica del protocolo).

## Cómo probarlo sin tocar tu sesión real
`tests/smoke_test.py` arma un proyecto y sesiones sintéticas en una carpeta temporal y comprueba el mapa, el hook y la búsqueda. **Prueba siempre sobre copias:** abrir un índice real con otro modo lo vacía (se regenera, pero la prueba sale en ceros), y el hook guarda por sesión cuánto texto inyectó, así que pruébalo con un `session_id` distinto por mensaje.
