---
name: actualizar-directivas
description: Aplica el protocolo para anotar órdenes nuevas del usuario en el archivo de directivas sin romper las existentes, regenerar el mapa y dejar respaldo, memoria y registro.
---

# Actualizar directivas

Cuando el usuario diga «actualiza directivas» (o «anota esto en las directivas»), sigue `docs/protocolo-actualizar-directivas.md`:
1. **Qué anotar:** las órdenes textuales del usuario en esta conversación que aún no estén en `.context/directivas.md` (verifica con `grep`; dilo en una línea, no esperes un sí). Opiniones («creo que…») se preguntan.
2. **Respaldo:** `python3 -I scripts/directivas-buscador/directivas_buscador.py actualizar antes "<tema>"`.
3. **Edita** con cambios puntuales: si ya hay una del mismo tema, se edita ahí con `_(actualizado AAAA-MM-DD HH:MM)_`; si una orden nueva contradice una anterior, el texto superado se mueve textual a `.context/directivas-historial.md`.
4. **Palabras de disparo:** si es una situación nueva, una línea en `.context/directivas-disparadores.tsv`.
5. **Mecánica:** `python3 -I scripts/directivas-buscador/directivas_buscador.py actualizar despues` (regenera el mapa, comprueba desfases y mide la recuperación de memorias).
6. **Memoria y registro:** memoria (forma corta en `MEMORY.md`), fila en `docs/registro-de-cambios.md` y línea en el changelog.
7. Responde en 3 o 4 líneas: qué directivas, en qué sección y línea, qué se verificó y qué quedó sin cambiar.
