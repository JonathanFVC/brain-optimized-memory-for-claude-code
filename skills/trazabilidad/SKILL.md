---
name: trazabilidad
description: Deja el camino escrito de cada tarea resuelta (qué se hizo, decisiones, cifras, gotchas y cómo repetirlo) y verifica trazabilidad previa antes de empezar una tarea parecida.
---

# Trazabilidad

**Antes de empezar** una tarea: busca si ya existe trazabilidad del mismo tema (`docs/`, memoria y conversaciones pasadas con la skill `buscar-conversaciones`) y parte de ahí.

**Al terminar** satisfactoriamente (o cuando el usuario diga «guarda trazabilidad»), sin preguntar:
1. **Documento** `docs/<tema>.md` con un resumen de una línea al inicio, qué se hizo y por qué, decisiones, cifras medidas, trampas y cómo repetirlo.
2. **Índice y changelog:** una línea en `.context/indice.md` y otra con fecha y hora en `.context/changelog.md`.
3. **Dónde va cada aprendizaje:** una regla del usuario → directiva; una preferencia o un hecho corto → memoria (una línea en `MEMORY.md` con la forma corta `- archivo.md`); un error propio → `anti-patterns.md`; un cambio al propio sistema → `docs/registro-de-cambios.md` (qué, por qué, medición, cómo revertir).
4. Di en **una línea** qué quedó y dónde.

Nunca guardes secretos en estos archivos si el proyecto se va a publicar.
