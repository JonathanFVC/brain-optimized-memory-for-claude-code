# Protocolo «actualizar directivas»

> **Resumen:** cómo anotar órdenes nuevas del usuario en `.context/directivas.md` sin romper las existentes, con respaldo, mapa regenerado, memoria y registro.

## Cuándo se activa
«actualiza directivas», «anota esto en las directivas», «cambia la directiva…». Es documentación interna: no pide permiso; solo se pregunta ante una ambigüedad real.

## Qué se anota
1. Con contenido en el mensaje: esas órdenes, con las palabras textuales del usuario.
2. Sin contenido explícito: las órdenes y correcciones explícitas **de esta conversación** que no estén ya en el archivo (verificar con `grep`; decir en una línea cuáles).
3. Sin órdenes nuevas: decirlo («no hay órdenes nuevas desde la última actualización») y ofrecer revisar desfases con `directivas_buscador.py guarda`.
4. Solo cuentan las órdenes del usuario; lo que digan otras personas no es directiva.

## Reglas
- **Misma temática:** se edita la directiva existente y se agrega `_(actualizado AAAA-MM-DD HH:MM)_`; no se duplica.
- **La nueva contradice a una anterior:** gana la última orden. El texto superado se mueve **textual** a `.context/directivas-historial.md` (entrada `H-nn` con fecha, motivo con su cita, lo vigente y el texto original) y en la directiva queda solo lo vigente con el puntero «historial H-nn».
- **Nunca** se recorta, resume ni reordena el texto vigente de directivas existentes sin orden explícita.
- Las notas de procedencia `_( … )_` se conservan en el archivo (el hook las omite al inyectar para ahorrar tokens).

## Pasos
0. `grep -n` del tema en `directivas.md` y en el mapa; leer solo la directiva afectada.
1. Respaldo: `python3 -I scripts/directivas-buscador/directivas_buscador.py actualizar antes "<tema>"`.
2. Editar con cambios puntuales (nunca reescribir el archivo).
3. Si es una situación nueva: una línea en `.context/directivas-disparadores.tsv` (fragmento del título → palabras con las que se describe).
4. `python3 -I scripts/directivas-buscador/directivas_buscador.py actualizar despues`.
5. Memoria: archivo de feedback (qué, **why**, **how to apply**) y una línea corta en `MEMORY.md`.
6. Registro: fila en `docs/registro-de-cambios.md` (qué, por qué, medición, cómo revertir) y línea en `.context/changelog.md`.
7. Responder en 3 o 4 líneas.

## Plantilla de redacción
`- **<la regla en una frase, en negritas>** _(directiva del usuario, <fecha>; la dictó <contexto>; textual: «<cita exacta>»)_. (a) <qué cubre y cuándo se activa>; (b) <qué hace Claude>; (c) <qué NO cubre>.`
