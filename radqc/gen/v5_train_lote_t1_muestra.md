# Tanda 1 train v5 — muestra de revisión (10 casos al azar, semilla 41, Spark Open, taxonomía-v4.1)

Marcar cada caso: `- [x] ✅` o `- [x] ❌ — comentario: ...`.

## T1-0050 · omision (error) — TC de cráneo simple

Motivo: Trauma craneal leve; descartar lesión intracraneal.

Correcto — INDICACIÓN: Hombre de 43 años con trauma craneal leve, estudio solicitado para descartar lesión intracraneal.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de colecciones hemáticas intra o extraaxiales ni signos de contusión o edema. Sistema ventricular, cisternas basales y surcos de la convexidad de amplitud normal, con línea media centrada. No se identifican trazos de fractura en calota ni en base de cráneo. Como hallazgo incidental se observa lesión extraaxial hiperdensa de 28 mm en la convexidad frontal izquierda, de bordes bien definidos y base de implantación dural, sugestiva de meningioma, con leve efecto compresivo sobre el parénquima adyacente y que requiere correlación con resonancia magnética contrastada y valoración por neurocirugía.
Correcto — IMPRESIÓN: No se identifica hemorragia ni lesión intracraneal de origen traumático agudo. Lesión extraaxial de 28 mm en convexidad frontal izquierda sugestiva de meningioma que requiere estudio complementario con resonancia magnética y valoración por neurocirugía.
Variante — INDICACIÓN: Hombre de 43 años con trauma craneal leve, estudio solicitado para descartar lesión intracraneal.
Variante — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de colecciones hemáticas intra o extraaxiales ni signos de contusión o edema. Sistema ventricular, cisternas basales y surcos de la convexidad de amplitud normal, con línea media centrada. No se identifican trazos de fractura en calota ni en base de cráneo. Como hallazgo incidental se observa lesión extraaxial hiperdensa de 28 mm en la convexidad frontal izquierda, de bordes bien definidos y base de implantación dural, sugestiva de meningioma, con leve efecto compresivo sobre el parénquima adyacente y que requiere correlación con resonancia magnética contrastada y valoración por neurocirugía.
Variante — IMPRESIÓN: No se identifica hemorragia ni lesión intracraneal de origen traumático agudo.
Esperado [omitted_finding/error]: body='Como hallazgo incidental se observa lesión extraaxial hiperdensa de 28 mm en la convexidad frontal izquierda, de bordes bien definidos y base de implantación dural, sugestiva de meningioma, con leve efecto compresivo sobre el parénquima adyacente y que requiere correlación con resonancia magnética contrastada y valoración por neurocirugía.' impresion='' (HALLAZGOS describe lesión extraaxial de 28 mm sugestiva de meningioma que requiere estudio adicional y la IMPRESIÓN no la menciona.)

- [ ] ✅ / ❌ — comentario:

## T1-0044 · doble_chequeo (verify) — RX de abdomen

Motivo: Dolor abdominal súbito y defensa; descartar neumoperitoneo.

Correcto — INDICACIÓN: Dolor abdominal súbito y defensa; descartar neumoperitoneo.
Correcto — HALLAZGOS: Distribución fisiológica del gas intestinal sin dilatación de asas ni niveles hidroaéreos. No se identifica aire libre subdiafragmático ni neumoperitoneo. Siluetas renales y sombras del psoas de aspecto conservado. No se observan calcificaciones ni litiasis radiopaca evidente. Estructuras óseas sin lesiones agudas.
Correcto — IMPRESIÓN: Radiografía de abdomen sin signos de neumoperitoneo ni obstrucción intestinal. No se identifican alteraciones agudas.
Variante — INDICACIÓN: Dolor abdominal súbito y defensa; descartar neumoperitoneo.
Variante — HALLAZGOS: Distribución normal del gas intestinal, sin niveles hidroaéreos ni neumoperitoneo. Siluetas renales y psoas de aspecto usual. Sin litiasis radiopaca evidente. Estructuras óseas sin lesiones agudas.
Variante — IMPRESIÓN: Radiografía de abdomen sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar neumoperitoneo' impresion='Radiografía de abdomen sin alteraciones agudas.' (La indicación plantea descartar neumoperitoneo como pregunta crítica y el cuerpo responde pero la conclusión no nombra explícitamente la patología, por lo que requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## T1-0031 · doble_chequeo (verify) — RX de tórax

Motivo: Dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.

Correcto — INDICACIÓN: Hombre de 39 años con dolor torácico súbito tras procedimiento para descartar neumotórax a tensión.
Correcto — HALLAZGOS: Pulmones adecuadamente expandidos, sin consolidaciones, atelectasias ni derrame pleural. No se identifica neumotórax ni signos de tensión mediastinal. Silueta cardiomediastínica de tamaño y contorno dentro de límites normales. Estructuras óseas del tórax sin lesiones agudas visibles.
Correcto — IMPRESIÓN: Radiografía de tórax sin evidencia de neumotórax a tensión ni otras alteraciones agudas.
Variante — INDICACIÓN: Hombre de 39 años con dolor torácico súbito tras procedimiento para descartar neumotórax a tensión.
Variante — HALLAZGOS: Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame pleural. Silueta cardiomediastínica de tamaño y contorno normales. Sin neumotórax. Estructuras óseas del tórax sin lesiones agudas.
Variante — IMPRESIÓN: Radiografía de tórax sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar neumotórax a tensión' impresion='Radiografía de tórax sin alteraciones agudas.' (Caso de doble chequeo: la indicación interroga neumotórax a tensión y el cuerpo responde pero la conclusión es genérica sin nombrar la patología, requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## T1-0023 · control_menores (control) — RX de rodilla

Motivo: Dolor crónico; valoración de cambios degenerativos.

Correcto — INDICACIÓN: Hombre de 60 años con dolor crónico en rodilla para valoración de cambios degenerativos.
Correcto — HALLAZGOS: Radiografías anteroposterior y lateral de rodilla derecha. Mineralización ósea conservada sin lesiones líticas ni blásticas. Espacios articulares femorotibial y patelofemoral conservados con pequeño osteofito marginal de 2 mm en el cóndilo femoral medial. No se evidencia derrame articular ni alteraciones significativas de partes blandas.
Correcto — IMPRESIÓN: Rodilla derecha sin alteraciones agudas. Alineación conservada sin fractura ni luxación.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T1-0051 · doble_chequeo (verify) — TC de cráneo simple

Motivo: Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.

Correcto — INDICACIÓN: Hombre de 38 años con Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.
Correcto — HALLAZGOS: Parénquima cerebral de densidad conservada, sin evidencia de hematomas intra o extraaxiales ni focos de contusión hemorrágica. Sistema ventricular de tamaño y morfología normales, sin hidrocefalia ni efecto de masa. Cisternas de la base permeables y surcos de la convexidad conservados. Línea media centrada, sin desviación. Estructuras óseas de la calota y base del cráneo sin trazos de fractura.
Correcto — IMPRESIÓN: TC de cráneo simple sin evidencia de hematoma ni hemorragia intracraneal aguda. No se observan fracturas ni efecto de masa.
Variante — INDICACIÓN: Hombre de 38 años con Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.
Variante — HALLAZGOS: Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea media centrada. Sin fracturas.
Variante — IMPRESIÓN: TC de cráneo simple sin alteraciones agudas.
Esperado [doble_chequeo/verify]: body='descartar hematoma' impresion='TC de cráneo simple sin alteraciones agudas.' (Caso de doble chequeo con motivo crítico en la indicación informado con plantilla normal; el cuerpo responde pero la conclusión no nombra explícitamente la patología crítica y requiere verificación humana.)

- [ ] ✅ / ❌ — comentario:

## T1-0076 · control_limitacion (control) — RX de abdomen

Motivo: Control de litiasis renal conocida.

Correcto — INDICACIÓN: Control de litiasis renal conocida en mujer de 57 años.
Correcto — HALLAZGOS: Radiografía de abdomen en proyección anteroposterior con técnica adecuada y exposición suficiente. No se identifican con certeza imágenes calcificadas definidas sobre las siluetas renales ni en el trayecto ureteral esperado, con limitación por superposición de gas intestinal y material fecal en marco colónico. Siluetas renales de tamaño y contornos conservados dentro de lo evaluable. Distribución del gas intestinal sin signos de obstrucción ni neumoperitoneo; estructuras óseas sin alteraciones agudas.
Correcto — IMPRESIÓN: No se identifican imágenes calcificadas compatibles con litiasis renal en la radiografía actual; evaluación limitada por interposición de gas intestinal y baja sensibilidad del método para litos pequeños o poco calcificados.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T1-0092 · omision (error) — RX de rodilla

Motivo: Trauma en rodilla; descartar fractura.

Correcto — INDICACIÓN: Mujer de 19 años con trauma en rodilla, se solicita RX para descartar fractura.
Correcto — HALLAZGOS: Radiografía de rodilla en proyecciones anteroposterior y lateral con técnica adecuada. No se identifica trazo de fractura agudo ni derrame articular significativo. Se observa lesión lítica expansiva de 4,2 cm en metáfisis distal del fémur, de bordes irregulares, con ruptura cortical y reacción perióstica en sol naciente asociada a masa de tejidos blandos. Estructuras óseas restantes con densidad y alineación conservadas, sin otras alteraciones.
Correcto — IMPRESIÓN: No se evidencia fractura aguda. Lesión lítica agresiva de 4,2 cm en metáfisis distal del fémur sugestiva de neoplasia ósea primaria, requiere correlación con resonancia magnética y valoración por ortopedia oncológica.
Variante — INDICACIÓN: Mujer de 19 años con trauma en rodilla, se solicita RX para descartar fractura.
Variante — HALLAZGOS: Radiografía de rodilla en proyecciones anteroposterior y lateral con técnica adecuada. No se identifica trazo de fractura agudo ni derrame articular significativo. Se observa lesión lítica expansiva de 4,2 cm en metáfisis distal del fémur, de bordes irregulares, con ruptura cortical y reacción perióstica en sol naciente asociada a masa de tejidos blandos. Estructuras óseas restantes con densidad y alineación conservadas, sin otras alteraciones.
Variante — IMPRESIÓN: No se evidencia fractura aguda, sin otras alteraciones óseas evidentes.
Esperado [omitted_finding/error]: body='Se observa lesión lítica expansiva de 4,2 cm en metáfisis distal del fémur, de bordes irregulares, con ruptura cortical y reacción perióstica en sol naciente asociada a masa de tejidos blandos.' impresion='' (HALLAZGOS describe lesión lítica agresiva de 4,2 cm que cambia el manejo y requiere estudio adicional, pero la IMPRESIÓN la omite por completo.)

- [ ] ✅ / ❌ — comentario:

## T1-0038 · control_dimension (control) — RX de tórax

Motivo: Trauma torácico cerrado; descartar fracturas costales.

Correcto — INDICACIÓN: Hombre de 88 años con trauma torácico cerrado, se solicita radiografía de tórax para descartar fracturas costales.
Correcto — HALLAZGOS: Radiografía de tórax PA y lateral. Se identifica opacidad nodular de bordes bien definidos en lóbulo superior derecho que mide 32 x 25 x 20 mm, sin cavitación ni calcificaciones. No se evidencian trazos de fractura costal ni alteraciones de la alineación ósea. No hay neumotórax ni derrame pleural. Silueta cardiomediastinal dentro de límites normales para la edad, con aorta torácica elongada y ateromatosa.
Correcto — IMPRESIÓN: No se observan fracturas costales ni neumotórax. Nódulo pulmonar en lóbulo superior derecho de 32 mm, se sugiere correlación con tomografía de tórax.
Variante: ninguna (control).

- [ ] ✅ / ❌ — comentario:

## T1-0072 · omision (error) — Angio-TC de tórax

Motivo: Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.

Correcto — INDICACIÓN: Hombre de 84 años con dolor torácico y dímero D elevado; se solicita angio-TC de tórax para descartar tromboembolismo pulmonar.
Correcto — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del tronco pulmonar y sus ramas principales y segmentarias, sin defectos de llenado endoluminal compatibles con tromboembolismo pulmonar agudo. Se identifica nódulo pulmonar sólido espiculado en el lóbulo superior derecho de 18 mm asociado a adenopatía hiliar derecha de 12 mm, sugestivo de proceso neoplásico primario. No se observan consolidaciones, derrame pleural ni neumotórax. Aorta torácica y estructuras mediastinales sin alteraciones agudas, sin disección ni aneurisma.
Correcto — IMPRESIÓN: No hay signos de tromboembolismo pulmonar agudo. Nódulo pulmonar sólido espiculado de 18 mm en lóbulo superior derecho con adenopatía hiliar de 12 mm, sugestivo de neoplasia pulmonar; requiere correlación histopatológica y valoración por neumología.
Variante — INDICACIÓN: Hombre de 84 años con dolor torácico y dímero D elevado; se solicita angio-TC de tórax para descartar tromboembolismo pulmonar.
Variante — HALLAZGOS: Angio-TC de tórax con adecuada opacificación del tronco pulmonar y sus ramas principales y segmentarias, sin defectos de llenado endoluminal compatibles con tromboembolismo pulmonar agudo. Se identifica nódulo pulmonar sólido espiculado en el lóbulo superior derecho de 18 mm asociado a adenopatía hiliar derecha de 12 mm, sugestivo de proceso neoplásico primario. No se observan consolidaciones, derrame pleural ni neumotórax. Aorta torácica y estructuras mediastinales sin alteraciones agudas, sin disección ni aneurisma.
Variante — IMPRESIÓN: No hay signos de tromboembolismo pulmonar agudo. No se observan consolidaciones ni derrame pleural.
Esperado [omitted_finding/error]: body='Se identifica nódulo pulmonar sólido espiculado en el lóbulo superior derecho de 18 mm asociado a adenopatía hiliar derecha de 12 mm, sugestivo de proceso neoplásico primario.' impresion='' (HALLAZGOS describe nódulo pulmonar espiculado de 18 mm con adenopatía sugestivo de neoplasia que requiere estudio adicional y la IMPRESIÓN lo omite.)

- [ ] ✅ / ❌ — comentario:

## T1-0037 · pregunta (error) — RX de abdomen

Motivo: Distensión y vómito; descartar obstrucción intestinal.

Correcto — INDICACIÓN: Hombre de 37 años con distensión abdominal y vómito, para descartar obstrucción intestinal.
Correcto — HALLAZGOS: Radiografía de abdomen en decúbito y bipedestación con distensión de asas de intestino delgado en hemiabdomen central, con calibre máximo de 38 mm y múltiples niveles hidroaéreos escalonados. Hallazgos compatibles con obstrucción intestinal de intestino delgado. Colon con escasa cantidad de gas sin dilatación y sin signos de neumoperitoneo. Estructuras óseas visualizadas sin lesiones agudas.
Correcto — IMPRESIÓN: Obstrucción intestinal de intestino delgado con asas dilatadas hasta 38 mm y niveles hidroaéreos. No se observa neumoperitoneo.
Variante — INDICACIÓN: Hombre de 37 años con distensión abdominal y vómito, para descartar obstrucción intestinal.
Variante — HALLAZGOS: Radiografía de abdomen en decúbito y bipedestación con distensión de asas de intestino delgado en hemiabdomen central, con calibre máximo de 38 mm y múltiples niveles hidroaéreos escalonados. Hallazgos compatibles con obstrucción intestinal de intestino delgado. Colon con escasa cantidad de gas sin dilatación y sin signos de neumoperitoneo. Estructuras óseas visualizadas sin lesiones agudas.
Variante — IMPRESIÓN: Distribución anómala del gas intestinal con asas centrales dilatadas de hasta 38 mm. Estructuras óseas sin alteraciones agudas.
Esperado [indication_unanswered/error]: body='descartar obstrucción intestinal' impresion='Distribución anómala del gas intestinal con asas centrales dilatadas de hasta 38 mm. Estructuras óseas sin alteraciones agudas.' (La indicación pregunta por obstrucción intestinal crítica y el cuerpo responde pero la conclusión no la nombra explícitamente.)

- [ ] ✅ / ❌ — comentario:
