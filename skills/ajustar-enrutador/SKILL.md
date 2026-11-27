---
name: ajustar-enrutador
description: Cuando el usuario pregunta si se puede ajustar, afinar o calibrar el enrutador de búsqueda, responde que sí y guíalo por etapas (estado, etiquetar una muestra propia, congelar, probar reglas en una copia aparte, validar a ciegas, respaldar y promover solo si cumple) para asegurar la precisión.
---

# Ajustar el enrutador (por etapas)

Usa esta skill cuando el usuario pregunte **si se puede ajustar, afinar o calibrar** el enrutador de búsqueda (`scripts/buscador/enrutar_busqueda.py`). La respuesta es **sí**, y se hace **por etapas**, sin cambiar nada en caliente y sin prometer una cifra: la precisión se mide con los mensajes del propio usuario.

## Dos caminos que conviven
1. **Automático, con el uso:** el enrutador arranca buscando en las dos fuentes (V1 carpeta + V2 conversaciones) y, con las marcas de tus tareas, cada regla va eligiendo sola la combinación más barata que cubra lo que hizo falta (solo V1, solo V2, las dos o ninguna = en vivo). Pide ≈ 25 marcas coherentes por regla. Se ve con `python3 -I scripts/buscador/buscar_todo.py --calibracion`.
2. **Manual, por etapas** (lo de abajo), para ajustar reglas o temas propios cuando el usuario quiere acelerar o corregir un patrón.

## Etapas (no saltarse ninguna)
1. **Estado.** Corre `--calibracion` y explica en pocas líneas qué reglas tienen marcas, cuáles se estrecharon y cuánto falta. Pregunta qué patrón le falla al usuario.
2. **Muestra etiquetada.** Toma unos 40 a 60 mensajes reales suyos (sin mostrarlos fuera de su equipo), propón tú la etiqueta de cada uno (`conv`, `carp`, `ambas`, `ninguna` o `vago`) y **que el usuario corrija**: su corrección es la verdad. Guarda la muestra solo en su carpeta de datos.
3. **Congelar y fijar criterios antes de medir.** Copia el enrutador actual (huella SHA-256) y escribe los criterios de aceptación: (a) coincide con las etiquetas ≥ el actual; (b) por pares, gana ≥ pierde; (c) «no busca cuando debía» ≤ el actual + 1; (d) tokens por mensaje ≤ el actual + 10 %.
4. **Reglas o temas en una copia aparte.** Propón cambios (nuevas reglas, o filas en `.context/enrutador-temas.tsv`: raíz de palabra, fuente, nota) **en una copia**, nunca sobre la instalación en uso.
5. **Validar a ciegas.** Pide una tanda **nueva** de mensajes que las reglas no hayan visto, etiquétala sin mirar la decisión del enrutador y compara contra el congelado y el candidato.
6. **Respaldar y promover solo si cumple los cuatro criterios.** Respalda lo que se va a reemplazar, promueve, verifica con `python3 -I tests/test_enrutador.py` y deja la trazabilidad (qué cambió, cifras, cómo revertir). Si no cumple, no se promueve y se dice por qué.
7. **Dejar activo el calibrado automático** y revisar `--calibracion` de vez en cuando. Las marcas las pones tú (Claude) **cuando detectas que se cumplieron los criterios de la tarea**, no al terminar la conversación: `buscar_todo.py --marca v1|v2|ambas|ninguna <tarea> [--id <búsqueda>]`.

## Reglas
- No inventes cifras ni prometas «X % de acierto»: mide con los mensajes del usuario y repórtalo con sus límites (las reglas ajustadas a una muestra quedan optimistas: valida con mensajes nuevos).
- No guardes ni muestres el texto de sus mensajes fuera de su equipo; el registro de uso guarda solo señales.
- Los modelos generales (embeddings, clasificadores) no mejoraron a las reglas en las pruebas del autor; el ajuste útil es de reglas y temas propios.
