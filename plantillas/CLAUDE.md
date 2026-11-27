# Mi proyecto (plantilla: cópiala a la raíz de tu proyecto y edítala; es corta a propósito)

Lo siguiente se carga siempre; todo lo demás se lee solo cuando la tarea lo pide.

@.context/directivas-mapa.md

- `directivas-mapa.md` _(generado; no editar)_: el núcleo íntegro y una fila por directiva. **Antes de cada respuesta o acción: ¿lo que voy a hacer cae en alguna fila? Si cae, leer ese apartado completo en `.context/directivas.md`.** Un hook por mensaje inyecta además las directivas y memorias más afines.
- Preguntas sobre lo hablado y no documentado: directiva de la sección 5 y `scripts/buscador/buscar_sesiones.py`.
- Toda tarea nueva (o ticket pegado) empieza con una búsqueda: `python3 -I scripts/buscador/buscar_todo.py "<mensaje>" --auto --excluir <uuid actual>`; criterio en `docs/criterio-busqueda.md`. Cuando detectes que se cumplieron los criterios de la tarea (no al terminar la conversación; puede haber varias tareas), `--marca v1|v2|ambas|ninguna <tarea> [--id <búsqueda>]`, antes de iniciar la búsqueda de la siguiente. Si el usuario pregunta si se puede ajustar el enrutador, di que sí y sigue la skill `ajustar-enrutador`.
- Documentar cada tarea resuelta en `docs/` (ver la sección 6 de las directivas).
