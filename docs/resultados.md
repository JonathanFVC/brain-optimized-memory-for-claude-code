# Resultados, lecciones y lo que no funcionó

> **Resumen:** mediciones del autor sobre su propio historial (≈ 6,000 turnos, 183 preguntas de control): V2 solo 0.467 de MRR, ligero ≈ 0.60, profundo ≈ 0.63; ningún reordenador abierto probado fue significativamente mejor que otro; un modelo propio pequeño entrenado por destilación no superó a V2.

## Método
Preguntas de control con una **ancla** (expresión regular que identifica el turno correcto; validada dentro de ese turno y en pocos turnos del índice). Tres tandas: 92 preguntas, 54 difíciles (paráfrasis fuertes, vagas, con ruido, de dos pasos) y 37 nuevas; parte las escribió Claude a partir de turnos reales. Métricas: top 5, 1.º lugar y MRR (tope de 2 resultados por sesión); intervalos de confianza al 95 % con bootstrap pareado de la diferencia de MRR. **Es un solo historial y una sola persona:** úsalo como orientación y mide con tus propias preguntas (`scripts/buscador/evaluacion/evaluar_metodos.py`).

## Modos (183 preguntas)
| Modo | Top 5 | 1.º | MRR | Comando completo |
|---|---|---|---|---|
| V2 solo | 58 % | 38 % | 0.467 | ≈ 0.1 s |
| Ligero (V2 → reordenador) | 70 % | 54 % | ≈ 0.60 | ≈ 7 s |
| Profundo (V2 + vectores → reordenador) | 73 % | 56 % | ≈ 0.63 | ≈ 9 s |
El profundo gana sobre todo en **paráfrasis** (MRR 0.854 contra 0.750 del ligero en la primera tanda); en preguntas de «dos pasos» (que necesitan dos turnos) todos fallan casi siempre.

## Reordenadores y vectores comparados (92 preguntas, reordenando V2 + vectores)
Reordenador gte-multilingual (0.730, 0.36 s por consulta) · Qwen3-Reranker-0.6B (0.745, 2.4 s) · bge-reranker-v2-m3 (0.735, 2.5 s). Ninguna diferencia fue significativa; se eligió gte por costo (1/7 del tiempo). Vectores: e5-small bastó (Qwen3-Embedding-0.6B costó 9 veces más sin ganar). La pareja Qwen3 + gte sumó ≈ +0.02 de MRR (no significativo) a 2.9 s por consulta.

## ¿Y los modelos sin V2?
Con los mismos modelos pero sin BM25: **e5 solo 0.357** (peor que V2 solo); e5 → gte con 20, 50 y 100 candidatos: 0.496, 0.555 y **0.591**; contra el profundo (0.625) la diferencia con 100 candidatos no es significativa (−0.034, IC95 [−0.087, +0.017]) pero cuesta 5 veces más trabajo del reordenador. Con 100 candidatos gana en las preguntas difíciles (0.534 contra 0.475) y pierde en las literales. La respuesta correcta estaba entre los 100 primeros candidatos en 153 de 183 preguntas con vectores y en 163 con BM25: se complementan.

## Lo que no funcionó: un modelo propio pequeño
Se probó una «bolsa de raíces» (vectores de palabras iniciados con e5 más un peso por palabra) entrenada por **destilación** de dos reordenadores (≈ 4,700 preguntas calificadas por los maestros). Resultado: solo MRR 0.208; reordenando los 20 de V2, 0.351 contra 0.466 de V2; mezclado con V2, −0.037. Causas probables: sin contexto no capta paráfrasis, vectores iniciales de palabras sueltas, y consultas sintéticas con mucho traslape de palabras con su turno. **Lección:** con pocos miles de ejemplos conviene usar modelos preentrenados y medirlos, no entrenar uno desde cero. Si se retoma: afinar `e5-small` (un transformer) con negativos duros, etiquetas de un cross-encoder y consultas reales.

## Cómo se entrenaron los dos modelos (fuentes públicas)
- **multilingual-e5-small** ([informe técnico](https://arxiv.org/abs/2402.05672)): parte de un transformer preentrenado; ≈ 1,000 millones de pares con pérdida contrastiva y, después, ≈ 1.6 millones de ejemplos etiquetados con negativos duros y destilación de un cross-encoder.
- **gte-multilingual-reranker-base** ([mGTE](https://arxiv.org/abs/2407.19669)): encoder de ≈ 300 M de parámetros entrenado desde cero con MLM sobre ≈ 1 billón de tokens y luego un cross-encoder con pérdida contrastiva y negativos duros.
- **Receta general para adaptar un modelo a un dominio chico** (resumen de la literatura, no verificada aquí): consultas del dominio, negativos duros de un buen recuperador, etiquetas de un cross-encoder y destilación (mejor listwise y junto con la pérdida contrastiva).

## Lecciones operativas
- **Prueba sobre copias del índice y de los vectores.** Abrir el índice real en otro modo lo vació y borró los vectores; todo se regenera, pero la prueba salió en ceros.
- **Prueba el hook con una sesión distinta por mensaje:** con una sola, el tope por sesión lo calla y parece roto.
- **Los números de línea de las directivas se mueven** al agregar una: en las pruebas, resuélvelos por el texto.
- **«hoy» no debe tapar otra fecha** («el mes pasado hablamos de X, ¿cómo lo cambiaría hoy?»).
- **Pega consultas cortas y específicas** al buscador; con el mensaje completo se diluye el ranking.

## Comparativas: conjuntos de preguntas y cómo leerlas
Las cifras de la imagen y del README salen de **conjuntos distintos** y no se pueden mezclar:
- **183 preguntas** (92 + 54 difíciles + 37 nuevas): comparativas finales (modos, modelos sin V2, reordenadores).
- **92 preguntas** (documentadas y no documentadas): «el camino» (de la búsqueda solo en carpeta hasta el reordenador). Clasificación objetiva: *documentada* = el ancla de la respuesta aparece en documentos o memorias (57); *no documentada* = no aparece (35), por eso la búsqueda en carpeta saca 0 % ahí **por construcción**.
- **77 preguntas** (48 independientes + 29 de calibración): vectores solos contra BM25 y afinación de BM25.
- **48 preguntas independientes** (redactadas por un subagente a partir de turnos aleatorios, anclas validadas): búsqueda en carpeta 19 % contra índice de sesiones 54 %.
Sesgos a tener presentes: las preguntas las redactaron modelos y no la persona; la respuesta siempre existe en el índice de sesiones (los métodos de sesiones parten con ventaja sobre la búsqueda en carpeta); las cifras con pocas preguntas tienen intervalos amplios; las evaluaciones de herramientas de terceros son de octubre y noviembre de 2026 y se hicieron leyendo documentación, README y código (solo graphify se ejecutó, sin LLM y sin llaves de API).

## Alternativas consideradas (resumen; la tabla completa está en el README)
Graph y RAG con grafos (graphify; no para recuperar conversaciones), servicio de vectores (Qdrant; innecesario: ≈ 22 mil vectores = ≈ 34 MB), solo semántico (e5-small 57 % y bge-m3 56 % contra BM25 61 %), modelo propio pequeño (MRR 0.208), matemática clásica entrenada (42 % sola), afinar BM25 (27 variantes y 64 configuraciones sin mejora), MemPalace (sus dos ideas probadas por separado: el índice de sesiones sí, el guardado al compactar no), servicios que envían texto fuera (mem4dev), plugins que resumen con un LLM (claude-mem), qmd (no probado) y Engram (no evaluado).
